# rulekit handoff

**Updated:** 2026-08-30
**Runtime checkpoint:** working tree on `main` (review batches 66–68
implemented; full synthetic and curated gates clean)
**Active campaign:** GSM8K Mining v2, M7 example-led vertical mining
**Immediate state:** all four published Mining v2 candidates are landed; no
candidate is awaiting human or machine review

This is the operational entry point. It records current state, durable
boundaries, and the next safe action. Completed increment narratives belong in
[`mining-log.md`](mining-log.md), measured dead ends in
[`negative-results.md`](negative-results.md), and design detail in the linked
plans and architecture document.

## Read first

1. [`../CLAUDE.md`](../CLAUDE.md) — constitution and standing gates.
2. [`architecture.md`](architecture.md) — current runtime and authoring
   architecture.
3. [`gsm8k-mining-v2-plan.md`](gsm8k-mining-v2-plan.md) — active campaign and
   promotion contract.
4. [`methodology.md`](methodology.md) — DEV/TEST firewall and precision policy.
5. [`generation-and-annotation-plan.md`](generation-and-annotation-plan.md) —
   implemented Designer product contract and milestone record.

## Current position

RuleKit is a deterministic controlled-English reader and reasoner. Language
knowledge lives in validated YAML packs; runtime Python provides grammatical,
fact, inference, and consumer machinery but contains no corpus vocabulary and
no per-question solvers. Generated examples and human reviews are authoring
evidence only and never enter the runtime registry.

The active mining method is M7:

1. select one currently declining GSM8K `dev-train` item;
2. record only its stable id and structural class, never its prose;
3. build invented end-to-end analogues and negative neighbours;
4. extend general grammar, inference, asks, and bounded YAML vocabulary;
5. pass synthetic tests before checking the original item locally by id;
6. publish an immutable candidate manifest for Designer review;
7. require exact human approval and the complete machine gate; and
8. integrate sequentially, then spend any protected look manually and
   deliberately.

The corpus sentence is never committed to tests, manifests, briefs, or docs.
One item can motivate an increment but cannot justify a one-off mechanism.
The shipped M7 increments are recorded in [`mining-log.md`](mining-log.md):
temporal event totals (130), task-completion duration gaps (131), and
anaphoric distance chains with exact combined totals (132).

### Latest implementation checkpoint

General physical-quantity support is no longer owned by the corpus-mined
pack. The reusable `physics` pack owns the generic ask family, the
`physics_quantity` category, ordinary speed, weight, momentum,
gravitational-potential-energy, and power formulas, and their minimal
vocabulary. The reusable `chemistry` pack owns atomic-mass data and the exact
molar-mass, moles-from-grams, cost-of-moles, and weight-of-moles asks; its
weight calculation reuses the physics formula and core mass conversion.
`curated` loads both directly, while `difg-mined` declares them as dependencies
and contributes only advanced extensions. Pack loading resolves manifest
dependencies transitively from sibling packs, so projects and tests do not
repeat the dependency graph. The physics consumer binds operands by their
declared dimensions through the shared `kernel/dimensions.py` algebra and
still declines on ambiguous, unread, or multiply stated values.

Qualified-package container questions now cover both separated per-package
statements and inline `N large bags with M items` / `N small bags of M items`
pairs. Explicit `them all`, `both bags`, and `the contents of both bags`
transfers resolve through the same quantity and totality facts. Portable
physical containers can reverse source-package and destination roles when the
surface explicitly states their size and contents. Capacity is a
separate evidence path: progressive wondering, checking, examining,
measuring, and studying frames establish inquiry context; complete-fit
evidence proves only a safe lower bound, while a remainder left after an
explicitly full container establishes an exact capacity. The generator now
realizes counted-qualified noun slots directly, so the inline package rule is
selectable and strict
round-trips instead of being reader-only. Core English owns the ordinary
vocabulary used by these reusable frames; malformed doubled prepositions stay
unread and decline.

Independent ask generation now covers every currently safe standalone token
domain. Project generation fixtures can declare bounded ISO dates, coordinate
points, and chemical formulae; each witness is validated by the ordinary
reader before it enters a slot domain. This makes nine previously blocked
GSM8K calendar, coordinate, and chemistry asks reviewable without putting
example values or corpus text in Python. The terminal measurement ask is also
generatable after declaring `final` compatible with the mass dimension and
requiring the natural definite noun phrase.

Generation exposed loose legacy chemistry and calendar contracts at the same
time. Calendar spans now require plural units. Molar calculations distinguish
counted amount-of-substance units, counted base-mass inputs, currency rates,
and the declared base mass unit instead of accepting any conversion unit in
any position. Nominal calendar, chemistry, and coordinate asks generate their
required definite articles. The standalone blockers are now deliberate
context boundaries rather than missing ordinary token domains. Scenario-aware
availability reports those asks as unavailable in `ask_only` while allowing
modes that can provide their required evidence.

Contextual ask generation is data-planned rather than consumer-specific. An
ask can declare either an `evidence` strategy with ordinary premise rules and
query-to-premise slot bindings, or a `conditional` strategy that embeds one
ordinary generated premise before an otherwise invalid uninverted question.
The normal reader and solver remain the only acceptance oracle, and the final
document must activate the exact target ask after ordinary discourse
resolution. This covers all fourteen curated context-only asks: discourse
group totals and per-holder answers, product-progress planning, measured
container contents, present and historical age groups, finite temporal
location witnesses, and the indirect conditional currency form. Complement
labels `boy` and `girl` now live in core English with their declared closed
pair, making that ask independently generatable outside the mined pack.

The latest review reconciliation tightened three semantic boundaries exposed
by generated examples. Predicate-noun partitions now use the directional
`category_contains` predicate: a declared superclass may contain a subtype,
but unrelated nouns and reversed superclass claims do not match or generate.
Task-completion durations now use the completion verb category's inherited
actor/theme frame, while pack-owned `homework` and `project` extend the
finishable-object vocabulary. Sequential-partition percentage asks require a
qualified plural destination such as `science courses`. Contextual ask replay
now rebuilds the complete reviewed document before checking the winning ask,
so a discourse-group pronoun retains its exact antecedent group instead of
spuriously regressing to the generic combined ask.

Goal vocabulary is now normalized by grammatical construction rather than by
individual premise wording:

- `goal_predicate` is the shared non-actual semantic parent. Its children
  distinguish finite infinitival predicates (`want`, `hope`, `intend`), direct
  quantity predicates (`need`, `require`), and priced-purpose resource
  activities (`save`, `raise`).
- The existing premise and ask ids remain stable for review replay, but their
  slots use those generic categories. Extending compatible vocabulary no
  longer requires another arithmetic rule.
- All variants still emit the same `Goal`; the surface predicate is retained
  only for traceability and the deficit consumer ignores it.
- Comparative goal relations now anchor only on another compatible `Goal` and
  derive a `Goal`. They cannot borrow an actual holding or materialize a
  current holding from a target comparison.
- Synthetic equivalence, negative-neighbour, inference-boundary, and strict
  generation tests cover all three construction families.

The latest consolidation moves positive lexical role knowledge out of grammar
rules and into extensible category relationships:

- `CategoryDef.selectional_roles` defines inherited actor/theme contracts for
  verb categories. Child categories may narrow, never broaden or replace a
  role with an unrelated target.
- `verb_roles_compatible` maps a construction's slots to those semantic roles.
  The registry selects one complete most-specific frame; sibling senses are
  alternatives and cannot be mixed.
- Bounded motion, completion, transfer, finding, enrollment, dropping,
  consumption, shucking, initiation, earning, production, teaching, and
  winning families now own their complete frames.
- `measure_holder_compatibility` and `measure_holder_compatible` provide the
  analogous extensible relationship for noun measures and plausible holders.
- Ordinary premise and ask clauses no longer restate an exact category-owned
  positive frame. A regression test scans both collections and allowlists only
  explicit construction-dependent slot mappings. Remaining
  `verb_role_compatible` clauses are construction-local facets, negative
  exclusions, or category-dependent slot mappings.
- The ask-side migration exposed and corrected one vocabulary omission:
  generic `money`, like `dollar`, is an earnable quantity object.

This means adding a compatible verb or noun normally extends every applicable
premise and ask through category membership; it should not require copying a
new pair of category checks into each rule.

The Designer now treats clean valid premise and ask reviews as durable
conformance evidence rather than inbox work. A valid verdict that still has a
selected defect or an incorrect/unclear interpretation or result remains
actionable and cannot become canonical evidence. Its default Reviews view
contains unresolved problems and regressed positive exemplars;
validated premise and ask coverage are grouped by vocabulary-independent
structural signature, and the complete append-only history remains paginated
in the evidence archive. One canonical clean-valid exemplar per group is replayed
against the current premise/fact or ask/query/answer contract. Resolution
preserves evidence; tombstoning explicitly excludes it. Premise generation
can target the least human-validated rule. Random ask generation advances the
least human-validated target and then an unseen surface branch, while the new
validated-premises scenario starts from exact replay-valid reviewed premises
and generates a declared ask that the normal solver can answer from them. Its
own frontier is counted separately: it advances unused reviewed premise-rule
families, semantic consumers, and ask targets before using fact/query overlap
as a tie-breaker. This stops already reviewed age questions from monopolizing
the pool when compatible rate evidence is available. Pack-declared validated
slot bindings align a counted ask span with the reviewed rate's unit and
denominator, so that evidence now yields a natural integral projection rather
than an arbitrary fractional count. Derivation-backed validated source
bindings preserve modality as well: reviewed “should” rate evidence can feed a
“should” ask but is not silently rewritten as past “did”. Review batch 62 also
tightened the original anchored-relation rule to finite, role-compatible,
non-goal predicates; made elided-measure asks count unresolved Relation
measures when testing ambiguity; and made possessed-place asks require an
owner-scoped place quantity rather than treating the owner as the place.
The conjoined same-holder anchor now has the corresponding complete boundary:
both clauses use the same finite possession surface, plural counts use a
count-compatible additive direction, and an explicit trailing adverb must be
compatible with that verb's surface tense. The relationship is declared in
category data and shared by matching and generation, so `currently` selects a
present holding while flexible anchors such as `still` may retain a past
holding. Event quantities and unrelated states can no longer borrow a
possession anchor. Core `bring` and `conduct` paradigms also expose their
singular/plural agreement explicitly.
Definite-pool fractions now use the governing verb's complete category-owned
actor/theme frame. Selectional roles may carry an inherited grammatical-number
constraint, allowing alternative senses such as plural collection addition,
mass or edible-material addition, plural livestock raising, and currency
raising without a rule-local word list. This rejects incompatible initiation
and reading objects and numeric parts of one shopper or living rabbit while
retaining plural collections, divisible materials, and edible portions.
Strict generation spells a unit share as `one ninth`; the reader deliberately
retains its older bare-unit compatibility. Extension-owned `seashell` is now a
declared transferable object, preserving the established sale-of-a-fraction
DEV class.
Goal predicates now inherit the general non-quantity-object exclusion as a
category relationship. Dedicated goal rules may still read `hope`, `require`,
`save`, and future vocabulary according to their declared complement grammar,
but ordinary ratio/event rules cannot reinterpret those non-actual targets as
actual quantities. The full times-as-many conjunct now requires a positive
common-noun standard and applies both declared measure/holder compatibility
and category-scoped theme frames. Theme mapping is deliberately scoped to
unambiguous consumption frames: established motion comparisons use the noun as
a distance measure rather than a verb theme, and existing human-validated
transfer/winning examples remain evidence. Length measures consequently apply
to the general `motion_participant` holder category, retaining person and
animal distance events without admitting non-moving actors.
Optional interpretation, result, and naturalness judgments keep grammatical
acceptance distinct from semantic and stylistic preference. This index remains
strictly authoring-only and does not enter the Registry or runtime inference.
Validated-premise search ranks all current exemplars for the selected ask
before bounding the premise pool, considers up to 32 random targets with eight
evidence checks each, and caches `generation.yaml` by exact file revision. Ask
reviews preserve aligned canonical premise-review ids. “Smallest answerable”
shows an explicit unchecked control for recording any generated companion
premise as clean reusable evidence; approving the ask alone never promotes it.
Ordinary solve, exact winning-ask, replay, and minimality checks remain
unchanged.

Temporal age asks now require evidence from their declared perspective.
Direct present/past age premises and relations retain their finite surface in
fact provenance; future/past offset premises that algebraically derive a
current age declare that result present. Relation and two-holder age-total
synthesis preserve the perspective and refuse cross-perspective anchors.
Absolute-year `AgeAtYear` projection and relative-day location witnesses keep
their stronger pre-existing coordinate contracts.

Measured content progress now separates a product's capacity from completed
work. A numeric hyphen compound such as a 100-page book records the book's
extent, while explicitly realized progress at two relative periods records
event quantities for the participant. The earlier period may be a qualified
duration such as `last week` or a bare declared past-day marker such as
`yesterday`; both retain their coordinates. A repeated explicit temporal
standard (`twice as many pages as yesterday`) must resolve to that same earlier
coordinate. A present-perfect ask totals only those
matching progress events, so the supported Mark example answers 30 rather
than treating all 100 pages as read. Bare qualified relative periods also
form an adjunct boundary: `cars last month` remains a quantity of cars timed
`last month`, never a compound quantity whose head is `month`.

A future planning ask can now request a bounded fraction of the unfinished
product: capacity minus completed matching progress, multiplied by the stated
fraction. The conditional desire clause is query structure and never asserts a
future event. Idiomatic `half the remaining pages` and productive `one fourth
of the remaining pages` are separate ask grammars. A conditional-first
paraphrase ("If ... tomorrow, how many ...?") remains one complete ask only
when its declared grammar consumes the whole sentence; otherwise the ordinary
leading-conditional premise split remains in force. All three require the same
participant, activity, measure, one linked product capacity, and a declared
future day marker. They remain unavailable as standalone asks, while the
answerable scenario now generates the required measured product and progress
history through those premise rules.

Activity-scoped wages now preserve why an elapsed duration is relevant.
`Natalia earns $12 an hour for gardening` records both the ordinary hourly
rate and an explicit gardening scope; `Yesterday she did 50 minutes of
gardening` records a dated activity duration. The rate-span consumer requires
participant and activity agreement before converting minutes to hours, so the
example answers 10 while tutoring time or a bare unrelated hour quantity
declines. Both premise rules have strict generation round trips. Auxiliary-
rooted categories are now a supported generic premise-generation domain;
`did` retains its single auxiliary sense, avoiding ambiguity in existing
questions. Declared restrictive focus markers support `only` and `just` both
before the activity verb and before its measured duration; unrelated adverbs
and duplicated focus positions remain outside the rule.
`babysitting` is now core-owned compensated-activity vocabulary rather than a
mined-pack-only noun. Curated therefore reads the same hourly-wage, focused
duration, and earnings ask without a new arithmetic rule; the exact DEV check
answers 10 and adds one safe GSM8K holdout commit (45 correct, zero wrong).

Purpose-scoped savings questions now preserve the purchase goal, current
progress, and committed contributions as separate evidence. A priced savings
premise records a target-qualified `Goal` for singular or plural purchase
objects; fraction progress admits both “half the money” and “half of the
money”; and the coordinated gift premise records one `Contribution` per
contributor without changing general holdings. The bounded “for that purpose”
adjunct is accepted only through the declared purpose preposition and noun.
The purpose-qualified deficit ask matches its purchase target and explicitly
opts into adding those contributions. Repeated possessive/object form is
expressed through the reusable `same_surface` predicate rather than trusting a
pronoun's nearest resolved referent. `wallet`, `parent`, `grandparent`, and
`purpose` are ordinary core-owned words with their semantic roles declared
separately. Strict generation can exercise both numbers in the otherwise
number-neutral target slot, while target/cost agreement remains enforced. The
new curated path answers the intended deficit and adds one safe GSM8K holdout
commit (46 correct, zero wrong).

Periodic measured output now has an opt-in counted-recipient cadence. A
declared unit-recipient output such as “Tova writes a 5-page letter to 3
friends twice a week” composes pages per product, recipient count, and
occurrences into one `Rate` (`30 pages/week`); the existing `rate-span`
consumer then performs the annual projection. `letter` opts into this frame,
while an ordinary book or an uncounted audience does not acquire a hidden
one-product-per-recipient assumption. The output-rate ask accepts both “in a
year” and the idiomatic bare span “a year”. The intended curated reading
answers 624, and the GSM8K DEV-holdout gate gains one correct commitment with
zero wrongs.

Review batch 66 separates authored surface quality from reader acceptance.
Premise rules can apply ordinary declarative predicates through
`generation_where`; this now makes the price-anaphor generator select
subject–verb agreement while preserving a human-validated marginal reading.
Indefinite articles choose `a` or `an` from the following generated surface,
with pronunciation exceptions owned by core category data. Explicit ratio
rules use the positive `quantity_comparison_verb` hierarchy, rejecting
unrelated speech, cognition, and generic activity verbs while retaining
quantity predicates, motion comparisons, and acquisition verbs such as
`catch`.

The same batch closes contextual generation for both explicit package-totality
transfer paraphrases. Context slots can share the target package/content
identity while independently choosing counts and distinct qualifiers.
`TotalityTransfer` now preserves explicit package and content heads, and
saturation refuses prior quantities whose package or content does not match.
Common-noun capacity inquirers are animate-gated; proper names remain valid.
The complete gate adds one net GSM8K DEV-train answer with no regression and
keeps every precision gate at zero wrong or incorrect commitments.

Review batch 67 closes the direct mass-comparison verb boundary across all
eight `as much` ratio and affine siblings. Their finite verb slots reuse the
positive `quantity_comparison_verb` hierarchy, so unrelated cognition,
containment, capacity, and enrollment predicates no longer become arithmetic
relations. Existing category-owned frames still apply their own object
constraints: edible sugar is valid for eating, money is not; transferable
materials and resources are valid transfer objects, while `rest` is not.
Elided contextual completion remains supported without admitting a direct
“finished ... water” object. Generator-only PP constraints also stop authored
possessive calendar phrases such as “during your year” without narrowing the
reader. The generic frame predicate now has an explicit
`require_declared_frame` option for constructions that must reject the
historical zero-frame open case; common verbs must not gain artificial child
frames merely to use it, because frame specificity affects every construction.

Review batch 68 joins descriptor, measure, and holder evidence into one
comparative route. A polysemous unit such as `year` is age-compatible under
`older` but duration-compatible under `longer`; proper-name permissions now
apply to the selected route rather than any unrelated membership. Dangling
comparatives also require a concrete counted offset unit, excluding abstract
dimension nouns such as `weight`, while valid mass comparisons of gardens and
measurement containers remain generatable.

Existential quantities now reject abstract/mass population heads, directional
goal prepositions, and topical modifiers whose counted host is not declared
topical. Optional `container of content` tails use the shared partitive
relationship: valid transferable contents and nested containers preserve the
container count, while an arbitrary tail such as `vessels of cost` cannot be
silently discarded. First- and second-person possessive determiners are
speech-anchored diagnostics rather than unresolved discourse defects, but
remain unbound so they cannot masquerade as entity slots. Positive review
replay treats removal of an old deficiency as monotone improvement and still
flags every newly introduced deficiency.

## Current measured baseline

These are the gates run at the current runtime checkpoint:

| Gate | Current result |
| --- | --- |
| full synthetic suite | 5,946 passed |
| curated suite | 71 correct, 0 wrong |
| GSM8K DEV-train | 107 correct, 0 wrong |
| GSM8K DEV-holdout | 46 correct, 0 wrong |
| ASDiv DEV | 46 correct, 0 wrong |
| SVAMP DEV | 24 correct, 0 wrong |
| MAWPS DEV | 11 correct, 0 wrong |
| SciBench DEV | 6 correct, 0 wrong |
| DIFG DEV | 75 correct, 0 wrong |
| FOLIO DEV | 0 numeric commitments |
| COGS DEV-train / holdout | 1,771 / 1,693 exact, 0 incorrect |
| PMB train / development | 117 / 4 exact, 0 incorrect |
| lint | 0 errors, 0 warnings |

Review batch 62 deliberately retired one DEV-train commitment that happened
to agree with its numeric gold while relying on an unsupported inference from
an owner's quantity to the contents of that owner's named container. The same
shortcut produced the human-rejected institution example. DEV-train therefore
moved from 107 to 106 correct with zero wrongs; explicit owner-qualified place
evidence still answers, while ownership alone now declines.
Review batch 66 later added one independent correct commitment, returning the
current total to 107 without weakening that owner/place boundary.

The latest protected GSM8K TEST look is look 126: 13 correct, 1 persistent
wrong, and 1,305 declined. Increment 132 made no new protected commitment.
Do not spend another protected look merely to refresh these numbers.

### Generation availability

Availability means “the authoring layer can realize the declared contract and
round-trip it through the ordinary matcher.” It does not mean that a human has
judged the resulting English or emitted fact valid.

| Project | Premise rules | Independent asks | Answerable asks |
| --- | ---: | ---: | ---: |
| curated | 159/168 | 115/133 | 129/133 |
| GSM8K | 153/160 | 153/166 | 166/166 |

The unsupported premise rows are deliberate safety interceptors or reader-only
rules, not ordinary generation targets. Fourteen curated and all thirteen
GSM8K independent-ask blockers require an antecedent discourse group,
measured-content or progress evidence, or embedded indirect-question syntax;
they become available only when answerable generation supplies that context.
The remaining four curated blockers are chemistry formula asks whose structural
formula fixture exists in the GSM8K project but is intentionally absent from
curated generation data.

Qualified package totals and complete transfers into containers now close one
more end-to-end arithmetic class. Indefinite size-qualified package statements
are explicit distributive rates; several package sizes may contribute to one
holder total. Contextual premise rules cover the pronoun form and both explicit
“both packages” paraphrases. Explicit package/content heads stay on
`TotalityTransfer`, so saturation requires the matching source package classes
and the one compatible content measure. The destination receives an inspectable
content event plus a stative quantity, which the generic definite
container-content ask reads. Definite single-package statements, mismatched or
mixed source contents, missing totality, and non-container destinations remain
decline boundaries. The motivating prose is not retained; invented analogues
pin the mechanism and its negative neighbours.

## Designer and promotion workflow

The Designer currently provides:

- strict-positive and controlled one-slot lexical-boundary premise generation;
- per-mode ask availability, independent ask generation, declared contextual
  evidence plans, bounded answerable-scenario search, and deliberate
  missing-evidence scenarios, plus explicit promotion of reviewed generated
  premises into reusable validated evidence;
- seeded reproduction, structural coverage objectives, compatible category
  filters, and terminal-blocker health;
- Reading-origin targeted reviews and targetless interpretation or
  missing-rule reviews;
- premise-, sentence-, and fact-attached defects with source navigation;
- allowlisted YAML editing with compile-and-rollback, followed by exact pinned
  retest and before/after comparison;
- append-only corrections, resolutions, and tombstones;
- action-only review triage, grouped premise/ask coverage, canonical positive
  replay, and a paginated evidence archive; and
- a Mining v2 queue with immutable manifests, isolated candidate runners,
  fingerprint-pinned human decisions, exact machine gates, and durable landing
  records.

Human reviews check the premises and facts that the authored grammar commits
to. They are not model-training labels. Hypotheses are deterministic,
trace-backed suggestions and never mutate YAML automatically.

The campaign queue currently contains four `landed` revisions and no open
revision. Old candidate and staging worktrees still exist locally; their
presence is not campaign state. Trust the append-only queue and landing ledger,
not directory names.

## Durable boundaries

- **Language knowledge is data.** Words, morphology, categories, selectional
  roles, compatibility relations, conversions, formulas, and reference facts
  live in packs.
- **Reading and answering are separate.** Premise rules emit facts; asks bind a
  normalized query to a generic consumer.
- **One fact store owns commitments.** Authoring views and benchmark adapters
  do not create a parallel inference system.
- **Ambiguity fails closed.** Missing, conflicting, incomplete, or multiply
  licensed evidence produces a decline or clarification, never a guess.
- **Generation uses the runtime, never the reverse.** Kernel, bench, lint, and
  guards do not import generation fixtures, ledgers, or review judgments.
- **Generated defects remain visible.** Generation exposes the actual authored
  boundary; it must not silently improve plausibility beyond the grammar.
- **A category relationship has one owner.** Grammar maps structural slots;
  category documents own extensible vocabulary relationships. Rule-local
  copies require a construction-level reason.
- **Reviews are append-only.** Editing, resolving, and tombstoning append new
  rows; they do not rewrite evidence.
- **Precision precedes coverage.** Every increment must retain zero new wrong
  answers and zero incorrect projected graphs across the standing gates.

## Next safe action

For another capability increment, run the M7 mining workflow on one new
inspectable GSM8K `dev-train` decline. Before publishing a candidate:

1. fold any new non-tombstoned Designer reviews that touch the intended class;
2. prefer an existing category relationship or generic mechanism over a new
   rule-local vocabulary list;
3. add invented positive, paraphrase, boundary, ambiguity, and decline tests;
4. run the complete standing gate; and
5. stop after publication for Designer human review and the exact machine
   gate.

If the immediate goal is consolidation rather than mining, continue auditing
the remaining legacy compatibility clauses. Migrate one only when the category
has one coherent complete frame; do not force overlapping facets or
construction-dependent slot mappings into a misleading hierarchy.

Useful commands:

```bash
uv run pytest -q -n 4 --dist=worksteal
uv run rulekit --project projects/curated bench --slice suite
uv run rulekit --project projects/gsm8k bench --slice dev-train --jobs 8
uv run rulekit --project projects/gsm8k bench --slice dev-holdout --jobs 8
uv run rulekit --project projects/gsm8k lint
uv run rulekit --project projects/curated campaign-queue
uv run rulekit --project projects/curated serve
```

Use the commands in [`../CLAUDE.md`](../CLAUDE.md) for the complete
cross-corpus and projection gate. A TEST-capable CLI flag is not authorization
to spend a protected look.

## Parked semantic-projection campaign

COGS/PMB semantic projection remains parked. The repaired Phase D baseline and
two subsequent DEV-only common-subject increments are retained at 100%
projected-edge precision. The known unsafe generic proper-object ditransitive
transfer was removed: direct proper objects remain themes, double-object
surfaces decline, and only the construction-specific explicit-`to` recipient
graph is retained.

Phase E is still blocked. The one permitted PMB protected standard-test
aggregate produced 1 exact and 0 incorrect but did not demonstrate the
required independent role classes. The external synthetic dataset candidate
at `/Users/louis/Development/semantic-generator` remains a separate review and
sealing concern. Do not inspect protected COGS/PMB rows, tune against that
aggregate, seal the external candidate, or build an importer without an
explicit campaign resumption.

On resumption, follow
[`semantic-projection-plan.md`](semantic-projection-plan.md) and
[`semantic-projection-ood-gate-plan.md`](semantic-projection-ood-gate-plan.md),
verify the external release and licence boundary first, and preregister the
one-way import and evaluation thresholds before evaluating it.

## Historical record

- [`mining-log.md`](mining-log.md) — shipped increments 129 onward.
- [`HANDOFF-archive-2026-07-23.md`](HANDOFF-archive-2026-07-23.md) — frozen
  Session 1–105 narrative.
- [`HANDOFF-archive-2026-07-16.md`](HANDOFF-archive-2026-07-16.md) — earlier
  arithmetic and mining narrative.
- [`negative-results.md`](negative-results.md) — measured failures and retired
  approaches.
- [`parked-physics-campaign.md`](parked-physics-campaign.md) — parked physics
  work.

Git history preserves the material pruned from this handoff. Do not append
per-review or per-increment narratives here again; promote only current state,
the next action, or a durable invariant.
