# rulekit handoff — generation workbench

**Updated:** 2026-08-04

**Active campaign:** deterministic rule generation and human review

**Status:** G1 through G4, G5a through G5g, G6, Reading-origin review,
targetless sentence-interpretation review, fact-level review, the
fraction-plural morphology correction, scoped
`GroupTotal`, and all eleven review-led grammar-boundary reconciliations are
complete and gated. The review-led adjective/noun compatibility boundary is
also complete and gated. The review-led leading-`GroupTotal` subject boundary
is complete and gated: existential `there` no longer becomes a group scope or
licenses an arbitrary verb. The Designer
can generate and explain one seeded sentence or promote
an exact Reading sentence through an explicitly selected actual premise-rule
match. It can also capture any non-question Reading sentence without a target
rule, preserve the intended interpretation or an optional missing-rule
suggestion, and keep that evidence out of premise-rule coverage. It can open
the implicated source, edit through the existing
compile-and-rollback boundary, retest the identical pinned sentence, compare
the before/after behavior, form evidence-bounded hypotheses, explore a
single-slot minimal pair, distinguish untouched from generated and reviewed
coverage, and deliberately probe a source-linked lexicon entry. Declared
plural, counted, bounded proper-name possessive, declared generic-pronoun, and
declared pronoun-category slots are realizable, as are categories rooted at
the lexicon sense `aggregate`. Category-qualified possessed nouns, exact slot
number, distinct possessive owners, many-to-many adjective/noun
compatibility, and negative slot-category constraints are now declarative
generation and matcher premises. G5h core ownership of all seven
project-empty exploratory category domains is complete: five more rules and
all compatible fillers are now available for human review. G5i recursive
optional-branch realization is also complete: 17 more rules are selectable,
nested branch state and exact sources are inspectable, and no unsupported
child is hidden by omission. G5j comparative-category realization is complete:
12 more rules are selectable through a category-generic realizer. G5k
sentence-wide `absent`-category realization is complete: ten more rules are
selectable, forbidden fillers cannot enter through broad or locked slots, and
the exact negative premise remains inspectable. G5l matcher-confirmed
`unbound` branch omission is complete: eight more rules are selectable and
their negative-lookahead branches, sentinel premises, locked-binding
conflicts, and probe exclusions are explicit. G5m `distinct_measure`
realization is complete: four more rules are selectable through exact
`(lemma, label, qualifier)` keys, including locked and minimal-pair
constraints. G5n direct complementizer-category realization is complete: the
mandatory and optional occurrences both draw from loaded lexical senses,
round-trip normally, and remain source-inspectable. G5o direct
quantifier-category realization is complete: all six core-owned fillers are
exposed for review, one rule unlocks, and the periodic sibling retains its
independent modal blocker. G5p remaining-blocker vocabulary ownership
profiling is complete. G5q core ownership of the two age comparatives is
complete: the dedicated age rule unlocks, additive direction memberships are
preserved, and combined-pack semantics remain identical. G5r dimension-
comparative core ownership is complete: all nine signed forms are reviewable,
the dimension rule unlocks, and combined-pack semantics remain identical.
G5s modal core ownership and slot realization is complete: all eight modal
forms are core-owned and reviewable, the broad and future-only domains remain
distinct, and four more rules unlock. G5t temporal-marker core ownership and
time-root realization is complete: both deictic markers are core-owned and
reviewable, and the standard-pinned future rule unlocks. G5u direct-adverb
visibility is complete: `currently` is core-owned, project-relative adverb
breadth remains visible, and all 99 curated premise rules are selectable. G5v
review-led premise auditing is active; eleven review batches are implemented
and fully gated. The latest adds referential comparative roles, declared
quantity-event participants, plural comparison-class standards, and exact
locative preposition/place compatibility.

**Active plan:**
[`generation-and-annotation-plan.md`](generation-and-annotation-plan.md)

**Parked campaign:** COGS/PMB semantic projection and the Phase E entry gate.
Its independent synthetic treebank candidate remains `pending_review`,
unsealed, and unimported. Do not mix that work into the active generation
workbench.

This is the short operational handoff. The complete Session 1–105 history is
preserved byte-for-byte in
[`HANDOFF-archive-2026-07-23.md`](HANDOFF-archive-2026-07-23.md). Do not extend
that archive; it is an immutable snapshot of the earlier arithmetic, FOLIO, and
semantic-projection work.

## Read before changing code

1. [`../CLAUDE.md`](../CLAUDE.md) — project constitution and standing gates.
2. [`generation-and-annotation-plan.md`](generation-and-annotation-plan.md) —
   active product contract, UI loop, architecture, and delivery increments.
3. [`architecture.md`](architecture.md) — current runtime architecture.
4. [`methodology.md`](methodology.md) — standing regression and precision
   discipline.

The generation plan is the detailed source of truth. This file records the
active increment and preserves the parked semantic-projection handoff below.

## Active objective

Add a clear, rapid rule-exploration mode to the RuleKit designer:

1. select or randomly choose a premise rule;
2. randomly realize one sentence from its match premises and project lexicon;
3. show why every premise passed;
4. let a human mark the sentence Valid, Invalid, or Unclear and attach defects
   to the implicated premises or surviving facts;
5. form deterministic, trace-backed hypotheses about rule or lexical changes;
6. open the relevant YAML in the existing editor;
7. save, compile, and rerun the identical sentence; and
8. show the before/after behavior before generating the next specimen.

Reading also supports a targetless interpretation review when no premise rule
consumed the sentence, or when the reviewer deliberately wants to describe
the sentence independently of incidental matches. These rows use
`review_kind: sentence` and `target_rule: null`; they may suggest a missing
rule but never fabricate one or mark rule/lexicon coverage reviewed.

This is interactive grammar debugging, not corpus fabrication or model
training. Reviews never alter runtime behavior automatically.

## Completed increments — G1 vertical slice through G6 plus G5c–G5g

G1 now provides:

- `src/rulekit/generation/`, isolated from the runtime import path;
- deterministic realization of flat `phase: read` premise rules from literals,
  simple slots, category domains, and `distinct`/`same_lemma`;
- `projects/curated/generation.yaml` for open proper-name fixtures;
- honest enumeration of all 93 curated premise rules: 8 supported in G1 and
  85 visible with exact blockers;
- ordinary-reader round trips with target `matched`/`shadowed`/`absent`,
  co-firing rules, facts, collisions, and deficiencies;
- Generate mode, seeded Generate next, Valid/Invalid/Unclear plus note, and
  Inspect in Reading; and
- fixed-path append-only review history under
  `projects/<project>/generation/reviews.jsonl`.

G2 adds:

- a Project-owned authoring source index for rules, asks, premise tokens,
  predicates, lexicon, categories and memberships, morphology, and numeric
  declarations;
- source-backed candidate premise rows with bindings, reasons, category
  ancestry, `where` outcomes, consumed units, and target specificity;
- explicit `unverified` rows when the target round trip is absent; and
- Generate-mode source controls that reuse the existing editable-document
  allowlist and jump to the exact source line.

G3 adds:

- deterministic fixed-sentence retesting without another realization pass;
- `POST /api/generation/retest`, which accepts the pinned sentence, target
  rule, seed, and prior bindings but no path or save authority;
- a Save + retest pinned action that first reuses `/api/doc` and its
  compile-and-rollback behavior;
- honest retest records when the target becomes absent, unsupported, or is
  removed from the reloaded project; and
- a compact before/after table for registry fingerprint, target status and
  specificity, premise outcomes, co-firing rules, facts, collisions, and
  deficiencies.

G4 adds:

- all declared defect choices with whole-sentence or exact-premise attachment;
- `POST /api/generation/hypotheses`, which replays the pinned sentence before
  deriving any suggestion from the current target, premise, shadowing,
  collision, morphology, lexical, and realizer evidence;
- source-linked advisory cards with explicit observations, notes, and
  open/confirmed/rejected/inconclusive statuses;
- an explicit no-mechanical-hypothesis result for unsupported evidence rather
  than a guessed recommendation;
- append-only persistence of bindings, defects, hypotheses, and status
  corrections in the existing fixed review ledger;
- locked candidate-review controls after capture, with all later status or
  verdict corrections routed through Review History → Edit; and
- `POST /api/generation/minimal-pair`, which excludes one selected filler,
  locks every other slot, preserves cross-slot constraints, and presents both
  premise tables without changing the runtime parser.

G5a adds:

- `type: plural` fillers drawn only from the loaded registry's declared,
  single-token plural surfaces;
- singular-lemma filler identity, preserving `distinct` and `same_lemma`;
- generator version `g5a` and generic current-realizer blocker wording; and
- exactly three newly selectable curated rules, moving support from 8/93 to
  11/93 without widening plain nouns or enabling counted, optional, or span
  slots.

G5b adds:

- `type: counted` fillers composed from declared non-negative integer values
  and declared single-token singular/plural noun pairs;
- exact agreement: count `1` selects the singular and every other admitted
  count selects the declared plural;
- singular-lemma filler identity for `distinct`/`same_lemma`;
- rule-token, number, lexicon, and conditional plural-morphology source
  evidence;
- generator version `g5b`; and
- exactly five newly selectable curated rules, moving support from 11/93 to
  16/93 without enabling any rule that retains an independent blocker.

G6 adds:

- a second fixed, schema-bounded Designer ledger at
  `generation/exploration.jsonl` for successful fresh realizations only;
- a separate fixed `generation/failures.jsonl` ledger for failed fresh
  attempts, scoped to the current registry fingerprint for frontier scoring;
- an honest fold of current availability, exploration observations, and live
  reviews into per-rule and reachable-lexicon successful, failed, attempted,
  and reviewed status;
- conservative legacy handling: the existing review marks its rule reviewed
  without fabricating a generation event or normalized filler review;
- deterministic least-attempted rule and filler selection with seeded,
  sorted tie-breaking;
- explicit compatible lexicon probing, exact incompatibility errors, and
  source navigation through the existing allowlist;
- no exploration writes for Reading promotion or pinned retest; and
- generator version `g6`, with the runtime, benchmark, retest, and hypothesis
  paths isolated from exploration metadata.

G5c adds:

- `type: possessed` fillers composed only from project-fixture single-token
  proper names and unambiguous declared single-token noun heads;
- exact `OWNER's HEAD` realization, gated by both the contraction declaration
  and the possessive lexicon declaration;
- singular-lemma identity for singular, declared plural, and invariant-plural
  heads, preserving the ordinary matcher's `distinct`/`same_lemma` behavior;
- rule-token, owner-fixture, contraction, possessive-lexicon, noun-lexicon,
  and conditional plural-morphology source evidence;
- generator version `g6-g5c`; and
- exactly one newly selectable curated rule, moving support from 16/93 to
  17/93 while its comparative affine sibling remains blocked.

G5d adds:

- direct `type: pronoun` fillers from every declared single-token pronoun
  lexicon entry, with exact surface identity and no hidden case or number
  repair;
- relocation of all 18 pronoun-only entries formerly owned by `difg-mined`
  into `core-english`, preserving the combined project inventory while making
  generic language available to core-only projects;
- relocation of `them`'s `pool_pronoun` membership beside the core category;
- rule-token and lexicon source evidence plus normal exploration identity;
- generator version `g6-g5d`; and
- exactly four newly selectable partition rules, moving support from 17/93 to
  21/93.

G5e adds:

- category-gated fillers for every declared category rooted at the grammatical
  `pronoun` sense;
- exact category membership plus root-sense filtering, without admitting the
  broader direct-pronoun domain;
- exact surface identity and rule-token, lexicon, category-membership, and
  ancestry evidence;
- generator version `g6-g5e`; and
- exactly one newly selectable curated rule, moving support from 21/93 to
  22/93.

The fraction-plural morphology correction adds:

- a declarative `fraction_plurals` mapping from each count-requiring plural
  surface to its singular fraction lemma in `core-english`;
- an incomplete-phrase marker on bare plural fractions, so `type: fraction`
  rejects `fifths` while the existing word-count merge admits `two fifths`;
- complete fraction generation from either a direct singular/complete surface
  or an explicit declared word count plus declared plural fraction form;
- singular-lemma filler identity and exact count, fraction-value, and
  fraction-morphology source evidence;
- generator version `g6-g5e-fractions`; and
- preservation of the invalid human review: its pinned
  `Dena had eighths of plum.` specimen now retests as `absent`, while
  `Dena had two eighths of plum.` matches normally.

G5f adds:

- generic category-gated fillers for the lexicon-sense root `aggregate`,
  using the same exact surface identity and category-path contract as the
  other supported roots;
- the complete loaded single-token domain: `altogether`, `average`,
  `combined`, `together`, and `total`, with no semantic filtering or silent
  repair;
- rule-token and lexicon source evidence for this degenerate root category,
  without fabricating a named category declaration or membership source;
- explicit empty-domain failure when no project-owned single-token aggregate
  lexicon entry exists;
- generator version `g6-g5f`; and
- exactly one newly selectable rule,
  `arithmetic/group-total-leading-marker`, moving support from 22/93 to 23/93
  while all three other aggregate occurrences retain their independent
  blockers.

G5g adds:

- relocation of generic `age/ages` and all three generic memberships
  (`age_noun`, `dimension_noun`, and `time_measure`) from `difg-mined` to
  `core-english`, preserving the combined inventory while correcting source
  ownership;
- `possessed: true` as an opt-in noun-category qualifier, plus exact
  `number: singular|plural` slot qualification in both matching and
  generation;
- `distinct_owner` as a cross-slot predicate for relations whose owned noun
  lemmas intentionally agree but whose owners must differ;
- copular, singular, owned-age premises for both possessive age comparison
  rules, with self-comparison rejected by the two-sided form;
- generator version `g6-g5g`; and
- the corrected exact support delta 23 → 26, unlocking
  `arithmetic/group-total-of-age`,
  `arithmetic/times-as-old-as-possessive-standard`, and
  `arithmetic/times-as-old-as-both-possessive`, while the sum-of-age sibling
  remains blocked by its optional group.

The review-led adjective/noun compatibility increment adds:

- `attribute_compatibility` as a pack-declared adjective-category to
  noun-category-list mapping. Words may carry several categories on either
  side, and any declared category pair licenses the predicate;
- `attribute_compatible: {attribute: SLOT, noun: SLOT}` as one ordinary
  matcher and generator `where` premise, with compilation checks for both slot
  roles and category-root correctness;
- compatibility filtering for fresh and locked/minimal-pair realization, plus
  exact premise explanations and source evidence for the pair, definitions,
  and memberships that licensed the specimen;
- core color, size, remnant, and ripeness boundaries, with `size_attribute`
  explicitly compatible with both physical-size and magnitude nouns;
- pack-local extensions for reference-owned `population` and the eight
  difg-backed DEV pairs, without moving or copying their lexicon entries;
- generator version `g6-attribute-compatibility`; and
- a precision-only narrowing of
  `arithmetic/partition-attribute-of-noun`: the current curated domain contains
  155 declared pairs—152 in generic core plus three reference-owned
  `population` pairs—while support remains 26/93 at that checkpoint.
  The invalid `10 of the years are large.` review now retests absent, and its
  append-only evidence remains untouched.

The review-led leading-`GroupTotal` subject-boundary increment adds:

- `slot_not_category: {slot: who, cat: existential}` to both scoped leading
  rules, retaining their broad action/state verb domain while refusing to
  treat existential `there` as a group identity;
- generic generation support for negative slot-category predicates, including
  fresh, locked, and minimal-pair fillers plus exact premise explanations;
- dedicated `In total there COPULA COUNTED` and
  `TOTALITY_MARKER there COPULA COUNTED` rules with declared number agreement;
- unscoped holding `GroupTotal` emissions for those existential surfaces and
  no commitment for arbitrary existential verbs such as the reviewed
  `Altogether there drops 2 coins.`;
- a totality-marker alternation that excludes `average`, whose broad
  `aggregate` lexical sense exists for average asks but cannot grammatically
  front an existential total; and
- generator version `g6-group-total-scope-boundary`, with availability moving
  from 26/93 to 28/95.

The complete inspected class contains 26 standing DEV matches: 25 retain
non-`there` scopes and their normalized verbs, while the sole existential
match reroutes to an unscoped holding total. The append-only review remains
live and unchanged; its pinned target now retests `absent`.

The Reading-origin entry adds:

- matched and shadowed premise-rule targets beside each non-question Reading
  sentence;
- explicit target selection when multiple rules fired;
- direct allowlisted YAML-editor controls for the selected premise rule,
  rule-backed decision details, emitted and semantic facts, and recognized ask
  rules, without first promoting the sentence into Generate mode;
- `POST /api/generation/from-reading`, which preserves the exact sentence,
  derives a stable identity seed, and performs no realization pass;
- `origin: generated|reading` on candidates and durable reviews; and
- reuse of the existing premise inspector, defect/hypothesis workflow,
  append-only history, and Save + retest path.

The fact-level review entry adds:

- hover guidance for every defect checkbox, stating the evidence a reviewer
  should look for;
- stable numbering for every surviving fact and source navigation when its
  emitting rule is indexed;
- exact fact choices in the existing defect-attachment selector;
- three explicit defect classes: an unjustified fact, an incorrect fact type
  or field, and a fact that omits downstream context;
- an immutable snapshot of the attached fact in the append-only review,
  including its type, fields, provenance rule, sentence index, and optional
  indexed source location; and
- source-linked hypotheses about the emitting rule while leaving runtime facts
  and reasoning unchanged.

The scoped `GroupTotal` increment resolves the semantic boundary exposed by
that fact review:

- `GroupTotal` now carries optional `scope`, and its conflict key is
  `(scope, measure)`;
- `arithmetic/group-total-leading` and
  `arithmetic/group-total-leading-marker` retain their exact normalized
  `who` binding as the scope;
- tail-only, existential, age, and synthesized totals remain unscoped rather
  than guessing an identity;
- different scopes over one measure coexist, while disagreement inside one
  scope and disagreement between unscoped totals still quarantine normally;
- named consumers admit only unscoped or exact-scope-compatible totals, and
  entity-less consumers never widen a scoped group to the whole scene; and
- both leading rules are structurally anchored at sentence start. This
  prevents a trailing marker in a longer clause from floating into the
  leading-marker rule with a conjunction misread as the group.

The original `missing_fact_context` review remains valuable historical
evidence. Its specimen now emits
`GroupTotal(measure="bird", value=40, scope="blue", verb="have")`, so a later
comparison mechanism can distinguish blue and red totals. This increment does
not invent that comparison ask or infer relationships between scopes.

The review-led grammar-boundary reconciliation then resolves every currently
invalid live review without rewriting its evidence:

- `plural_object_pronoun`, `copula`, and `plural_copula` narrow partition
  collections and predicates; cardinal partitions declare `same_number`,
  noun collections require their definite article, and membership predicates
  require plural nouns;
- `transfer_out ⊂ lose` keeps genuine recipient-bearing `gave`/`sold`
  surfaces while excluding consumption, ordinary loss, dropping, and
  spending;
- category slots can declare `counted: true`, and `arithmetic/stated-age`
  combines that with `age_measure`, a copula, and singular-name agreement;
- generic `year/years` plus its age/time memberships move from `difg-mined`
  to `core-english`, beside the grammar that needs them; and
- generator version `g6-reviewed-premise-boundaries` realizes and explains the same
  counted-category and grammatical-number constraints the matcher enforces.

All nine reviews that existed during that reconciliation were pinned and
retested: every invalid target
is now `absent`, while the valid `arithmetic/group-total-leading` specimen
remains `matched`. The ledger stays append-only and unchanged.

Current validation on 2026-07-27:

- the 3,900-test full repository gate passes in four-worker mode, including
  the 155-pair complete curated compatibility-domain check, all eight standing
  DEV pairs, 48 seeded
  compatible round trips, a generic two-target invented category, locked
  realization, provenance, compile failures, the preserved review, and direct
  Reading source references for rules, asks, decisions, facts, and semantic
  facts, plus the complete G5h ownership map, retained mining-pack extensions,
  recursive optional profiling, exact nested token sources, deterministic
  include/omit/inactive inspection, minimal-pair branch preservation, the
  complete comparative occurrence map, invented comparative vocabulary,
  deliberate probes of all three core delta members, the complete 14-rule /
  17-predicate `absent` map, invented forbidden-category filtering, exact
  negative-premise explanations, exploration exclusion, the complete
  eight-rule / nine-sentinel `unbound` map, nearest-branch omission, nested
  locked-sibling preservation, forbidden sentinel locks, the complete
  four-rule / five-pair `distinct_measure` map, qualifier- and label-aware
  keys, linked-domain availability, locked and minimal-pair preservation,
  exploration placement filtering, the complete mandatory/optional
  complementizer occurrence map, direct root-sense vocabulary, both
  complementizer exploration placements, the complete quantifier occurrence
  and six-filler maps, the two-word age ownership and combined-registry
  equivalence checks, the nine-word signed dimension ownership class, the
  complete five-occurrence modal map, all eight broad-modal and both
  future-modal filler checks, legacy combined-registry equivalence, guarded
  numeric resampling, the complete temporal-marker occurrence and ownership
  maps, both marker round trips, an invented time-rooted vocabulary check, the
  complete direct-adverb occurrence and ownership maps, matcher-confirmed
  included and omitted adverb branches, an invented adverb-root check, all 45
  combined-project adverbs retained as inspectable placements, the exact
  95/95 availability and 150-filler frontier, and one reviewable matching
  specimen for each newly exposed G5h–G5u rule;
- curated suite remains 65/65, 0 wrong, 100% precision;
- GSM8K DEV-train remains 104 correct / 0 wrong and DEV-holdout remains
  40 / 0, with both snapshot diffs neutral;
- ASDiv remains 44 / 0, SVAMP 30 / 0, MAWPS 9 / 0, SciBench 6 / 0, and
  FOLIO makes zero commitments;
- lint remains at 0 errors and two known warnings: the fraction-rule shadow
  and the documented totality-marker alternation; and
- G3 live validation pinned `Discount of 15%.`, showed
  `1/7 changed · identical sentence preserved`, exercised rollback, and
  restored the original fingerprint; G4 live validation generated
  `4% discount.`, rerolled only `pct` to `10% discount.`, produced a
  source-linked broad-gate hypothesis, returned the explicit unsupported
  fallback for a grammaticality defect, and preserved a status correction
  through append-only history. G5a live validation showed the plural premise's
  lexicon and morphology sources and rerolled `flowers` to `fish` while
  holding the other three slots fixed. Reading-origin live validation promoted
  `4% discount.` through its explicit
  `arithmetic/discount-percent-noun` match, preserved the sentence and actual
  binding, and enabled the normal verdict flow without recording the probe.
  G5b live validation generated matched
  `Bira sold Eron 19 rabbits.` for `arithmetic/transfer-ditransitive`, linked
  the counted premise to all four declaration surfaces, and rerolled only
  `item` to `10 eggs` while holding giver, verb, and recipient fixed. G6 live
  validation selected untouched `rabbit`, opened `core.yaml:187`, generated
  matched `Eron gives 18 rabbits to Aven.` for
  `arithmetic/transfer-prepositional`, and showed the rule and both sampled
  lexical identities as generated-but-unreviewed. G5c live validation then
  generated matched `Bira has double Cato's plum.` for
  `arithmetic/times-as-many-possessive-standard`, showed generator
  `g6-g5c`, and exposed the owner fixture, contraction, possessive declaration,
  noun declaration, and rule source. G5d live validation selected the
  core-owned `them` entry and generated matched
  `70 of them are blue.` for `arithmetic/partition-attribute`, with exact
  pronoun evidence and honest unresolved-context deficiencies. G5e live
  validation selected core-owned `it` and generated matched
  `Eron has half of it.` for `arithmetic/fraction-of-pronoun`, displaying the
  exact membership, category ancestry, and unresolved-reference deficiency.
  The fraction correction live validation generated matched
  `Cato received nine fifths of it.`, showed the explicit count and singular
  `fifth` lemma, linked all three numeric declarations, and produced no
  browser diagnostics. G5f live validation generated matched
  `Together they bought 9 books.` for
  `arithmetic/group-total-leading-marker`, reported generator `g6-g5f`,
  displayed `together → aggregate` with its rule-token and lexicon sources,
  emitted `GroupTotal`, and produced no browser diagnostics.
  Fact-level live validation numbered that fact, exposed all checkbox
  explanations, enabled the three fact-specific defects only after selecting
  the fact, and formed a source-linked missing-context hypothesis without
  recording a review.
  Scoped-`GroupTotal` live validation then generated
  `Combined everyone walked 16 friends.` on the current workspace server and
  displayed
  `{"measure":"friend","value":16,"scope":"everyone","verb":"walk"}` in both
  the surviving-facts card and the fact-attachment selector.
  The earlier probes left no human review, their temporary events were removed
  without touching live user-authored ledger rows, and the browser console
  remained clean. The scoped probe also left no review; its two temporary
  exploration events were removed while preserving the user's original
  `Total blue has 40 birds.` event.

## Test workflow

Use the smallest relevant synthetic file or `-k` expression while editing,
then run the complete parallel synthetic gate before declaring an increment
green:

```sh
uv run pytest -q tests/test_generation_workbench.py -k aggregate
uv run pytest -n 4 --dist=worksteal
```

The serial equivalent remains `uv run pytest`. Relevant-only and last-failed
runs shorten the inner loop; they do not replace the complete synthetic gate
or any standing benchmark, lint, snapshot, and precision gate required by the
constitution.

`tests/conftest.py` now shares unchanged repository packs, compiled registries,
projects, and parquet datasets inside each pytest worker. Temporary paths
always bypass the cache, cached dataset calls return a fresh list of frozen
items, and production processes are untouched. Set `RULEKIT_TEST_CACHE=0` for
a focused loader/debug run that must exercise every physical reload.

Do not use `--last-failed` as the standard inner loop: removed or renamed test
node IDs can leave stale cache entries and make it fall back to the entire
suite. An explicit file and `-k` expression has visible, deterministic scope.

Local reference timings on 2026-07-26:

- collection: 76.7 seconds → 1.89 seconds;
- full serial: 625.42 seconds → 37.87 seconds;
- full four-worker gate: 16.41 seconds; and
- corpus-string constitution audit: 18.92 seconds → 1.52 seconds.

The duplicate audit did not justify deleting tests: the repeated bodies
mostly exercise different module-owned rule sets and negative-neighbour
matrices, and fixture reuse removed their meaningful runtime cost. Broadly
disabling traces was also rejected as a default because the isolated saving
was only about 15.5% and several tests specify trace behavior directly.

## Active step — continue the G5v review-led premise audit

The adjective/noun compatibility and leading-`GroupTotal` subject reviews are
reconciled as complete declarative classes, not `year`/`large` or
`there`/`drops` exceptions. Their candidates, exploration history, and
append-only review rows remain user-authored evidence and must continue to be
preserved.

The next action is to generate or inspect the next least-explored premise and
review it in the Designer. The ten reviews handled by the third G5v batch,
the two handled by the fourth batch, the twelve handled by the fifth batch,
the five handled by the sixth batch, the five handled by the seventh batch,
and the two malformed surfaces handled by the eighth batch all retest
`absent`; its two intended-valid surfaces now match. Keep their
append-only evidence, and reopen a fixed class only if a pinned retest
regresses or a new neighboring review shows the boundary is incomplete.

Generation is an exploratory microscope, not a linguistic-validity oracle.
If every declared token and predicate has a realizer and a project-backed
filler, the rule must remain selectable even when the resulting specimen
exposes a defect. `matched` means the ordinary matcher accepted the current
premises; only the human review determines whether those premises licensed
valid and useful language.

G5o originally profiled exactly two direct `quantifier`-rooted occurrences:
`arithmetic/existential-premise-distributive.q` and
`arithmetic/periodic-rate-every-span.freq`. Curated owns six direct fillers in
`core-english`: `all`, `each`, `every`, `much`, `no`, and `some`.

Adding that root to the existing category-generic generator unlocks only the
distributive rule. The periodic sibling remains honestly blocked because its
optional `type: modal` descendant has no current realizer or project-backed
filler. All six quantifiers can be locked, generate an ordinary
matcher-confirmed specimen, retain exact token and lexicon sources, and appear
in exploration only on the supported `q` placement. An invented project proves
the realizer is not tied to the curated surfaces.

That deliberately exposed that the rule description named `each`/`every`
while its authored `cat: quantifier` premise accepted all six words.
Generation did not silently narrow that contract. The fourth G5v human review
has now supplied the evidence for a dedicated `frequency_quantifier`: the
existential rule still exposes all six quantifiers, while the explicit-count
periodic placement admits only `every`.

The exact frontier is now 87 supported and 8 blocked, with the same 125
reachable lexicon identities. The cumulative generator version is
`g6-g5o-quantifiers`.

Continue G5 coverage rather than advancing to deferred question generation.
G5r moves all nine generic physical-dimension comparatives into
`core-english`. Six positive forms (`heavier`, `higher`, `larger`, `longer`,
`taller`, `wider`) carry `dimension_more`; three negative forms (`lighter`,
`shorter`, `smaller`) carry `dimension_less`. The mined-owned
`higher`/`lower` category memberships remain extensions.

The move unlocks exactly
`arithmetic/anchored-relation-postfix-dimension`, raises availability from 88
to 89, and raises reachable lexicon identities from 127 to 136. Every form
generates an ordinary matcher-confirmed specimen with exact lexical,
membership, category, polarity, and rule-token evidence.

The exhaustive ownership test reconstructs the legacy layout in memory and
compares every compiled registry field except the source fingerprint. A
core+arithmetic+difg project is semantically identical before and after:
positive forms retain mined `higher` where previously declared, negative
forms retain `lower`, and `wider` remains dimension-only. The cumulative
generator version is `g6-g5r-dimension-comparatives`.

G5s moved all eight generic modal declarations from `difg-mined` to
`core-english`: `can`, `could`, `may`, `might`, `must`, `should`, `will`, and
`would`. The first six carry `capacity_modal`; `will` and `would` carry
`future_modal`. `can` retains its noun sense, plural, and the mined-only
`litter` extension. An exhaustive in-memory reconstruction of the old
ownership layout proves that every combined-registry semantic field remains
identical except the source fingerprint.

The generator now treats direct `type: modal` as the complete loaded modal
lexicon domain and `type: future_modal` as its exact declared subtype. All
eight forms are reviewable on `arithmetic/periodic-rate-every-span`, while
only `will` and `would` can enter the four future slots. A capacity-modal lock
on a future-only slot fails at the filler-domain boundary. The newly exposed
periodic rule also revealed a zero-denominator sample: arithmetic failures
from the ordinary round trip now reject that attempt and resample
deterministically rather than crashing or presenting a false candidate.

G5s unlocks exactly the periodic rule and the three future rules without a
temporal marker. Availability is now 93/95 with 144 reachable lexicon
identities. The cumulative generator version is `g6-g5s-modals`.

G5t moved generic `now` and `today` plus their `temporal_marker` memberships
from `difg-mined` to `core-english`. The generator now admits categories
rooted at the loaded `time` sense; it does not carry a marker surface list.
Both words generate matcher-confirmed standard-pinned future relations with
exact `word → temporal_marker → time` ancestry. An invented project proves
that another time-sensed member follows the same path, and an in-memory
legacy reconstruction proves combined-pack registry semantics are unchanged.

G5t unlocks exactly
`arithmetic/temporal-offset-times-as-old-as-future-std-now`. Availability is
now 94/95 with 146 reachable lexicon identities. The cumulative generator
version is `g6-g5t-temporal-markers`.

G5u moved generic `currently` from `difg-mined` to `core-english` and admitted
the loaded direct `adverb` root to category-generic generation. Curated can
now exercise both `and currently has ...` and the optional bare
`and has ...` shape. An invented project proves that the realizer follows
loaded vocabulary, while a legacy in-memory reconstruction proves that the
ownership move leaves combined-pack registry semantics unchanged.

The generator deliberately does not narrow the authored `cat: adverb`
premise. A project loading `difg-mined` exposes all 45 single-token adverbs on
the placement, including surfaces that may produce awkward or absent round
trips. Those are review evidence, not candidates for silent filtering.

G5u unlocks the final
`arithmetic/anchored-relation-conjoined-anchor` rule. Curated premise
availability is now 95/95 with 147 reachable lexicon identities. The
cumulative generator version at that checkpoint was `g6-g5u-adverbs`.

Mechanical premise generation is complete, but human validation is not. At
that checkpoint the append-only fold contained:

- 64 never-generated, 26 generated-but-unreviewed, and 5 reviewed rules;
- 65 never-generated, 67 generated-but-unreviewed, and 16 reviewed reachable
  lexicon identities; and
- 168 recorded generation events and five current live reviews.

G5v is therefore an interactive review campaign, not another realizer:

1. use Generate next to select the least-explored compatible rule/filler;
2. review one sentence at a time as Valid, Invalid, or Unclear;
3. attach defects to exact premises or facts and form source-linked
   hypotheses;
4. make declarative YAML changes only when the human evidence warrants them;
5. retest the pinned sentence and rerun all standing gates after each accepted
   boundary change; and
6. keep the review and exploration ledgers append-only.

The first G5v batch fixes all five live reviewed surfaces without rewriting or
tombstoning their evidence:

- quantitative comparative subjects and verbs now refuse the narrow
  `non_quantity_holder` and `non_quantity_object_verb` categories and enforce
  explicit subject/verb number compatibility;
- `many` rules retain the open plural-noun domain while excluding the narrow
  `many_incompatible_noun` class, so established count nouns do not require an
  exhaustive allowlist;
- `much` rules use the declared `mass_quantity_noun` boundary;
- comparative appositive prefixes use `possessive_determiner`, `animate`, and
  `bound_requires_type` to require a proper-name standard only when the role
  prefix is present;
- optional comparative PPs require a referential object, with
  `bare_pp_object` as the explicit bare-adjunct exception;
- additive affine many/much rules use `quantity_delta`, excluding age-specific
  directions; and
- anaphoric conjuncts require an overt `that`/`this`, while the elided scalar
  relation requires `standalone: true` so a counted noun cannot double-fire.

All five pinned reviews from that batch retest `absent`; valid neighboring
constructions remain matcher-confirmed. At that checkpoint curated
availability remained 95/95 and the reachable lexicon frontier was 147.
Moving generic `this` into `core-english` added one valid probe identity,
while applying authored `slot_not_category` refusals to the exploration
catalogue retired the historical invalid `there`-as-holder placement.

Exploration compatibility now shares the realizer's slot-local category
boundary. Without that filter, least-explored selection could permanently
alternate among `need`, `take`, and `want` on
`arithmetic/affine-fraction-as-many`; every locked surface was explicitly
forbidden by the rule and therefore failed all 64 attempts. Those dead
placements are no longer advertised as compatible. The append-only event
that historically generated `there` through the now-forbidden holder slot
remains on disk, but it does not define current reachability.

Failed selected probes are now durable attempts rather than invisible
non-events. The success ledger and `generated_count` remain unchanged;
`failures.jsonl` supplies separate `failed_count` and `attempt_count` fields,
and least-explored selection ranks rules and fillers by attempts. A
failure-only item is shown as `attempted_failed`, the Designer refreshes the
frontier immediately after the failed request, and only rows matching the
current registry fingerprint affect ranking. This prevents any mechanically
unrealizable probe from starving untouched alternatives while allowing an
authored edit to reopen it for immediate testing.

The second G5v batch reconciles all six current live invalid reviews as
complete declarative boundaries:

- the age-comparison family uses copular agreement and a dedicated past-copula
  category, preventing ordinary lexical verbs from occupying its predicate;
- elapsed-duration rates require a counted `duration_measure`, a finite
  expletive duration verb, and a bare-form infinitive. The generator and
  matcher now share the same `bare_form` morphology check;
- physical-dimension comparatives use descriptor/noun compatibility, so
  linear, mass, and duration comparatives pair only with compatible measure
  families;
- the fraction-frame relation now requires its determiner, count-aggregate
  noun, plural item, repeated verb, and paired optional destination
  prepositions rather than accepting an incomplete prefix;
- optional many-conjunct PPs use the same compatibility mechanism for their
  preposition/object pairing, retaining declared locative and remainder
  constructions while rejecting arbitrary objects; and
- conjoined aggregate anchors enforce agreement and exclude narrow
  non-quantity holders and verbs, preventing generic `amount`/`number`
  surfaces from being treated as concrete group relations.

`same_presence` now couples optional slots declaratively, while
`bound_requires_category` applies a category premise only when its controlling
slot binds. Attribute compatibility accepts adjective-, comparative-, or
preposition-rooted descriptor categories against noun categories. Generic
`inch`, `pound`, and `travel` forms moved into `core-english`, beside the
grammar that consumes them; mined packs retain only their domain extensions.

All six current pinned reviews retest `absent`, and valid direct,
prepositional, present/past, compatible-dimension, duration, and aggregate
neighbors remain matcher-confirmed. Curated availability remains 95/95 and
the reachable lexicon frontier is now 150. The current generator version is
`g6-reviewed-premise-boundaries`. The live fold contains 48 never-generated,
41 generated-but-unreviewed, and 6 reviewed rules; its 150 reachable
identities contain 45 never-generated, 80 generated-but-unreviewed, and 25
reviewed fillers. The append-only success ledger contains 218 observations
and there are six current live reviews.

The complete gate is green: 3,900 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings.

The third G5v batch reconciles all ten new live invalid reviews as complete
boundaries:

- temporal age-offset rules require declared `age_measure` units, with exact
  singular/plural agreement for the intensified `N more years` form;
- desire goals separate a finite matrix desire verb from a bare infinitival
  complement through shared matcher/generator morphology;
- nominal count frames require a determiner, declared count-frame noun,
  plural item, additive count direction, and viable holders and verbs while
  preserving both established `amount of PLURAL` and `number of PLURAL`
  forms;
- optional repeated item nouns agree with their offset when present, without
  making the optional slot mandatory;
- quantitative PP objects and animate appositive standards use declared
  compatibility and determiner classes;
- explicit remainder membership separates collection and member noun
  categories, with generic `animal` moved into `core-english`; and
- `verb_role_compatible` applies animate/proper-name role requirements only
  when the selected verb belongs to the declared agentive class.

The benchmark snapshot caught and prevented an early overconstraint that
excluded valid `amount of frogs/apples` and singular `1 more gallon` forms.
The corrected boundary restores all four established GSM8K commitments while
retaining every reviewed rejection. All ten pinned reviews retest `absent`,
all ten target rules generate matcher-confirmed specimens across the bounded
seed test, curated remains 95/95, and the reachable lexicon frontier is now
151.

The live fold contains 32 never-generated, 53 generated-but-unreviewed, and
10 reviewed rules. Its 151 reachable identities contain 42 never-generated,
77 generated-but-unreviewed, and 32 reviewed fillers. The append-only success
ledger contains 234 observations; the review ledger contains 55 rows folded
to ten live reviews, and the separate failure ledger contains two historical
attempts.

The complete gate is green: 3,948 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with three
known warnings.

The fourth G5v batch reconciles both new live invalid reviews as general
boundaries:

- `arithmetic/periodic-rate-every-span` now requires the dedicated
  `frequency_quantifier` class and an explicitly counted
  `duration_measure`. When its optional modal binds, the general
  `bound_requires_form` predicate requires a bare following verb; ordinary
  non-modal finite clauses remain valid. This rejects the reviewed
  `should gets ... some 6 apples` class while preserving both
  `should get ... every 6 years` and `gets ... every 6 years`;
- the generic sales-verb category is now core-owned, and
  `verb_role_compatible` supports a declarative negative role category.
  `arithmetic/times-as-much` uses it to reject a sales verb whose mass object
  is a declared remnant, without closing the class to saleable mass nouns or
  to non-sales verbs. Its optional PP also reuses the existing declared
  preposition/noun compatibility boundary.

Both current pinned reviews retest `absent`, both target rules continue to
generate matcher-confirmed candidates, and valid neighboring constructions
are pinned. The live fold contains 30 never-generated, 63
generated-but-unreviewed, and 2 reviewed rules. Its 151 reachable identities
contain 39 never-generated, 101 generated-but-unreviewed, and 11 reviewed
fillers. The append-only success ledger contains 236 observations; the review
ledger contains 67 rows folded to two live reviews, and the separate failure
ledger retains two historical attempts.

The complete gate is green: 3,963 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with three
known warnings.

The fifth G5v batch reconciles all twelve new live invalid reviews as
declarative boundaries:

- the possessive-kinship anchored relation adds ordinary agreement and the
  existing narrow holder, verb, count-noun, and quantitative-PP constraints;
- the price-anaphor rule uses a dedicated `price_relation_verb` category,
  retaining copular and cost forms while excluding unrelated events;
- optional comparative PPs on the reviewed many and fraction families share
  the existing preposition/noun compatibility relation. The declared
  quantitative-location class now includes every valid location witnessed by
  the DEV snapshot, including `side`, while measure, population, and arbitrary
  animate nouns remain outside it;
- all five existential quantity-premise siblings require a copula and
  agreement, so constructional `there` cannot license an event verb;
- rest-of-pool applies ordinary agreement and the narrow
  `non_quantity_object_verb` refusal;
- affine comparison appositives require animate possessive determiners, the
  affine fraction-many form refuses the declared prepositional-frame verb
  class, and their optional PPs use the same compatibility relation;
- the optional noun in `partition-rest-attribute` is now checked against the
  adjective only when that noun is present. Bare discourse-backed `Rest were
  small` remains valid, while an explicit incompatible `ages/small` pair is
  rejected; and
- the generic `polarity_compatible` predicate compares each slot only inside
  its declared category scope. Percent-change events use it to reject an
  explicit increase verb with a decreasing direction while leaving
  direction-neutral event verbs valid.

All twelve reviewed surfaces retest `absent`; valid copular price, existential,
remainder, quantitative-location, affine, partition, and percent-direction
neighbors remain matcher-confirmed. The initial DEV snapshot correctly caught
three overconstrained valid location examples (`mall`, `wardrobe`, and
`wheel`); those nouns and the full-suite `side` example now belong to the
general quantitative-location class rather than receiving rule-specific
exceptions.

The live fold contains 10 never-generated, 73 generated-but-unreviewed, and
12 reviewed rules. Its 151 reachable identities contain 38 never-generated,
73 generated-but-unreviewed, and 40 reviewed fillers. The append-only success
ledger contains 256 observations; the review ledger contains 81 rows folded
to twelve live reviews. The separate failure ledger contains three historical
attempts, none matching the current registry fingerprint.

The complete gate is green: 4,004 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with three
known warnings.

The sixth G5v batch reconciles all five new invalid reviews as two shared
premise boundaries:

- `GroupTotal` premise rules now use the declared `group_total_marker`
  category rather than the broad `aggregate` sense. `average` remains an
  aggregate operation but can no longer assert a sum. Existential and
  trailing totals accept bare `altogether`/`combined`/`together`/`total` and
  the declared `in total` pairing; arbitrary `at`/`to`/`with` combinations
  are rejected through `group_total_preposition` plus conditional
  `prepositional_group_total_marker` compatibility. The aggregate root is now
  a legal category root, allowing this distinction without adding a second
  ambiguous lexical sense;
- bare and `that` count-frame relative clauses now require a repeated verb
  whose lemma matches the matrix verb and whose number agrees independently
  with the standard. Paired frame-head prepositions and optional counted
  duration spans remain explicit premises. This prevents an incomplete
  `that bird` tail and the reviewed `Garden lose` disagreement without
  narrowing complete clauses; and
- the measured DEV-holdout buyer exposed one missing morphology declaration:
  `drinks` is now explicitly singular. Its valid `... Paul drinks in one
  day` clause remains readable through the declared duration-span branch.

All five pinned surfaces retest `absent`, and every corrected target continues
to generate matcher-confirmed candidates across the bounded seed gate. The
append-only fold contains 289 successful exploration events and 108 review
rows; the existing corrections and tombstones leave five live reviews while
preserving every original row as evidence. Current coverage is
4 never-generated, 89 generated-but-unreviewed, and 2 reviewed rules; the 151
reachable lexicon identities are 38 never-generated, 98
generated-but-unreviewed, and 15 reviewed.

The complete gate is green: 4,033 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

The seventh G5v batch reconciles the five latest live reviews as three general
premise boundaries:

- possessive ratio relations now distinguish plural count standards from
  singular mass standards. Both the affine and non-affine families require a
  declared `possession_state`, a non-unit multiplier, grammatical count/mass
  direction and morphology, and a subject distinct from the possessive
  owner. The general `distinct_from_owner` predicate makes that final
  constraint inspectable; ordinary `distinct` compares the possessed noun
  lemma and cannot detect `Fia ... Fia's apples`;
- `arithmetic/times-as-much-elided-standard` now inherits the full sibling's
  declared sale/remnant and preposition/object compatibility premises. Both
  full and standard-elided mass relations refuse the separately declared
  frame-prepositional verb class when their own surface has no such frame;
  and
- `arithmetic/goal-need-comparative-quantity` owns the ordinary
  `WHO needs N fewer/more PLURAL than WHO` construction. It keeps
  `need_premise` goal-scoped instead of weakening the general
  `non_quantity_object_verb` refusal.

The first count/mass split correctly rejected the reviewed generations but
temporarily broke the established `$50 more than twice Cecil's money` buyer
by requiring a standalone offset. The benchmark diff caught that exact
regression; allowing both bare and explicitly measured offsets restored
`bacb0d512ef7` through the new mass sibling without reopening any reviewed
surface.

All five live target rules retest `absent`; the corrected comparative-need
surface and count/mass neighbours are matcher-confirmed. Curated premise
availability is 98/98. The append-only fold contains 298 successful
exploration events and five live reviews. Current coverage is 3
never-generated, 93 generated-but-unreviewed, and 2 reviewed rules; the 151
reachable lexicon identities are 38 never-generated, 98
generated-but-unreviewed, and 15 reviewed. There are no failures at the
current registry fingerprint.

The complete gate is green: 4,069 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 40/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 9/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

The eighth G5v batch reconciles four live reviews as four inspectable
boundaries and one fact-explanation addition:

- `arithmetic/affine-item-relation-clause` now requires a counted currency
  offset, the complete definite frame, a mass-currency measure, and a
  mass-compatible direction. Generic `money` is core-owned; mined packs only
  extend its domain. The malformed `Plum won 4 older than thrice dollar Dena
  won.` surface is absent, while the complete measured frame remains valid;
- fraction-delta comparisons are split into disjoint count and mass siblings.
  Count comparisons require a declared plural non-mass measure and count
  direction; mass comparisons require a declared mass measure and mass
  direction. Both retain agreement, quantitative-verb, distinct-standard,
  and optional PP compatibility premises. The reviewed singular/plural,
  adjective, and PP defects are absent;
- `twice as many/much` requires the overt `as`/`that`/`this` introducer and
  rejects a following explicit-standard continuation through inspectable
  `unbound` sentinels. The targetless `Mary gets twice as many.` interpretation
  now matches without weakening the explicit-standard families;
- implicitly derived plural surfaces receive the noun sense plus only
  non-noun senses licensed by a category explicitly declared on that plural
  surface. Thus `cans` is no longer fabricated as a verb, while an explicitly
  licensed form such as price-relation `costs` retains its verb reading; and
- generated facts now retain the applicable authored `emits` expression and
  its resolved bindings. The Designer exposes these under “How this fact was
  derived,” and exact review snapshots preserve the explanation without
  making it part of fact identity.

The benchmark gate caught an initially unsafe downstream consequence rather
than hiding it in the premise rule: once the valid anaphoric multiplier was
represented, a question ending in `originally` could incorrectly return its
current qualified anchor. A dedicated start-state ask now invokes the existing
event inversion. Histories containing differently qualified same-measure
events decline because the current scalar modifier representation cannot
prove whether the event is nested or disjoint. GSM8K DEV-holdout therefore
moves from 40/0 to 41/0 by solving `c3ac53fdd650`; the originally-marked buyer
returns to a safe decline.

Both malformed reviewed surfaces retest `absent`; the targetless anaphoric
surface and the comparative-need sentence now match their intended rules.
Curated premise availability is 99/99 with 152 reachable lexicon identities.
The append-only fold contains 314 successful generation events, 117 review
rows folded to four live reviews, and no failure under the current
fingerprint. Current rule coverage is 1 never-generated, 95
generated-but-unreviewed, and 3 reviewed; filler coverage is 37
never-generated, 101 generated-but-unreviewed, and 14 reviewed.

The complete gate is green: 4,103 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train remains 104/0 with a neutral diff and DEV-holdout is
41/0 with one solve, no break, and no new wrong commitment. ASDiv, SVAMP,
MAWPS, and SciBench are 44/0, 30/0, 10/0, and 6/0; FOLIO makes zero
commitments; and lint has zero errors with two known warnings. No protected
TEST look was spent.

The ninth G5v batch reconciles five live reviews as four general premise
boundaries:

- the item-elided conjunct comparison may omit location context entirely, but
  when the first count has a location, `same_presence` requires the comparative
  conjunct to provide its own compatible location. The unframed rule also
  refuses the declared frame-prepositional verb class, so
  `Plum traveled 90 cards on her garden and thrice as many.` cannot discard
  the verb's missing frame or the missing comparison context;
- located existentials require their place to be referential and compatible
  with the selected preposition. Article-bearing and possessive locations
  remain valid; `There are 40 fish of rabbit.` does not turn an arbitrary noun
  into a location;
- explicit standards in the full, item-elided, and affine fraction-`many`
  family are referential quantity holders. Proper names remain bare, common
  noun standards require definiteness, productive index labels such as
  `team A` provide structural definiteness, and the declared
  `non_quantity_holder` class excludes measures such as `inch`; and
- `arithmetic/fraction-as-much` applies the existing declared
  preposition/noun compatibility relation to its optional context, rejecting
  `to the plum` while preserving compatible and context-free forms.

All five pinned reviewed targets retest absent. Valid paired and context-free
conjuncts, located existentials, definite fraction standards, proper-name
standards, and compatible mass contexts remain matcher-confirmed. All six
affected rule forms generate only matched or shadowed candidates across the
bounded sixteen-seed gate. The recursive optional profile is now 52 rules,
126 groups, 33 nested groups, and maximum depth three; the increase is fully
explained by the paired conjunct context and optional possessive existential
location.

The full synthetic and cross-corpus gates exposed three retained neighbours
before this boundary could ship. The mined location class did not yet include
the already-tested `office` or ASDiv's valid `school`; adding those pack-owned
members preserved the located-existential class without admitting `rabbit`.
The general referential check recognizes both article-bearing noun phrases
and the parser's productive index label on `team A`, `jar B`, and similar
entities. The label case uses structural condense output already carried in
relation identity, not a lexical surface list.

The append-only fold contains 338 successful generation events and 126 review
rows folding to five live reviews. Current rule coverage is 1
never-generated, 93 generated-but-unreviewed, and 5 reviewed; filler coverage
is 36 never-generated, 96 generated-but-unreviewed, and 20 reviewed. There
are no failures under the current registry fingerprint. Curated remains
65/65, while GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with
neutral before/after diffs. No protected TEST look was spent.

The complete gate is green: 4,116 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

The tenth G5v batch closes the two open existential reviews:

- `There are 40 fish of rabbit.` was already rejected by the located rule,
  but the shorter bare sibling still accepted the prefix `There are 40 fish`.
  Optional continuation sentinels plus `unbound` now prevent a prepositional
  or complete conjunct tail from falling back to that partial reading when its
  longer construction fails;
- a declared `quantity_container` condition preserves the independently
  useful head count in valid container-content partitives such as
  `30 boxes of apples` and `15 shelves of boxes`. `fish` is not a container,
  so the reviewed `of rabbit` tail cannot borrow that exception; and
- both counted populations in the conjoined existential refuse the declared
  `mass_measure` class. Thus `There are 14 hamsters and 40 pounds.` cannot
  treat a weight amount as a second independently enumerable population, and
  the new bare continuation sentinel prevents it from silently retaining only
  the hamster count.

The DEV gate completed the existing location class with `bowl`, `class`,
`classroom`, `farm`, and `party`; idiomatic bare `in class` is separately
licensed through `bare_pp_object`. Those declarations retain ordinary located
existentials and ratio/distributive buyers without weakening the reviewed
surfaces.

Both open reviewed sentences now produce no existential-rule match. Valid
single-item, conjoined-population, located, distributive, and
container-partitive neighbours remain matcher-confirmed and generate only
matched or shadowed candidates across the bounded seed gate. The recursive
optional profile is now 53 rules, 129 groups, 33 nested groups, and maximum
depth three.

The append-only fold contains 351 successful generation events and 131 review
rows folding to two live reviews. Current rule coverage is 1 never-generated,
96 generated-but-unreviewed, and 2 reviewed; filler coverage is 33
never-generated, 114 generated-but-unreviewed, and 5 reviewed. There are no
failures under the current registry fingerprint.

The complete gate is green: 4,124 tests pass in four-worker mode; curated is
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

The eleventh G5v batch reconciles the remaining comparison review:

- `Population received thrice as many trees at your area as pencil.` no
  longer matches `arithmetic/times-as-many`. Singular common-noun subjects
  and standards must be complete references, while ordinary bare plural
  comparison classes such as `nickels as dimes` remain valid;
- quantity-changing event verbs require each common-noun actor to belong to
  the declared `quantity_event_participant` class. Proper names and resolved
  pronouns remain valid, and stative possession comparisons retain their
  broader holder semantics;
- a standard may be a declared event participant or a plural measured class.
  This preserves `toy soldiers as toy cars` without treating singular
  `pencil` as a recipient. The distinction is explicit through
  `allow_plural_class`, not guessed from a surface word;
- locative compatibility now distinguishes `in` locations, `on` surfaces,
  and `at` sites. `in your area` and `on the tree` remain valid, while
  `at your area` and `on the area` do not inherit a generic locative pass;
  and
- mined `quarter` now declares `quarters` as its plural, and the referential
  matcher's existing pack-category escape hatch records the `Bill` name
  homograph through `bare_entity_reference`. These preserve the two benchmark
  neighbours exposed by the safety gate without adding a word-specific parser
  branch; and
- demonstrative anaphors and comparative anaphors now have separate rules.
  `that many pounds` remains a valid measured demonstrative, while item-elided
  `as many`/`as much` rules decline as soon as an explicit measure follows.
  The former shared rule let a rejected complete comparison survive as a
  shorter anaphoric prefix.

The reviewed sentence retests absent from the complete comparison and both
anaphoric rule families. A received-event minimal pair with a teacher and
student matches and generates normally; possessive-state and bare-plural
comparison neighbours remain matcher-confirmed. The append-only
fold now contains 353 successful generation events and 134 review rows.
The rule split changes the registry fingerprint, so those historical reviews
are retained but none is current. Current rule coverage is 2 never-generated
and 99 generated-but-unreviewed; filler coverage is 33 never-generated and
119 generated-but-unreviewed. The optional profile is 55 rules, 131 groups,
33 nested groups, and maximum depth three. There are no current-fingerprint
failures.

The gate is green: 4,134 tests pass in four-worker mode; curated remains
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with neutral
diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0, and 6/0;
FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

The twelfth G5v batch reconciles the next mass-comparison review:

- `Cato spends nineteen tenths less rest with its remainder than your friend
  Eron.` no longer matches `arithmetic/fraction-delta-relation-mass`;
- `rest` remains a valid `mass_quantity_noun` for constructions such as
  `gets less rest`. Instead, the existing declarative `verb_role_compatible`
  boundary now requires a `spend_verb` object's measure to be `currency` in
  both count and mass delta rules. `spends less money` and `spends fewer
  dollars` remain valid;
- fractional-delta optional PPs still use the shared location compatibility
  table, but explicitly exclude `quantity_remainder_preposition`. `in the
  garden` remains valid, while `with the rest/remainder` stays available only
  to the conjunct constructions that own remnant semantics; and
- the new reusable `proportional_delta_compatible` predicate checks the
  fraction against declared direction polarity. Increases remain unbounded;
  decreases above 100% decline instead of emitting a negative Relation
  factor. Matcher, compiler, availability, generation, locked probes, and
  premise explanations share the boundary.

The reviewed sentence retests absent, and 32 generated mass-delta candidates
all match their target with non-negative factors, compatible spend objects,
and no remnant PP. The fold contains 354 exploration events and 136 review
rows folding to one live review. Rule coverage is 1 never-generated, 99
generated-but-unreviewed, and 1 reviewed; filler coverage is 33
never-generated, 111 generated-but-unreviewed, and 8 reviewed. There are no
current-fingerprint failures.

The gate is green: 4,149 tests pass in four-worker mode; curated remains
65/65; GSM8K DEV-train and DEV-holdout remain 104/0 and 41/0 with exact neutral
before/after diffs; ASDiv, SVAMP, MAWPS, and SciBench remain 44/0, 30/0, 10/0,
and 6/0; FOLIO makes zero commitments; and lint has zero errors with two known
warnings. No protected TEST look was spent.

Do not interpret 101/101 as proof that every sentence is valid, bulk-label the
frontier, or advance to deferred question generation before the premise audit
is mature enough for a deliberate product decision.

## Active invariants

- Generation tooling may call the existing kernel; the kernel may not import
  generation tooling or review data.
- Word-specific filler data lives in packs or project generation fixtures,
  never Python.
- The generator reports parser behavior; the human judges rule validity.
- Hypotheses are inspectable suggestions and never automatic mutations.
- The current sentence remains reproducible by project fingerprint and seed.
- Saving uses the existing allowlist and compile-and-rollback boundary.
- Reviews are a small debugging history, not a train/test dataset.
- Existing runtime, bench, lint, and precision gates remain neutral when the
  generation feature is unused.

## Parked semantic-projection objective

When resumed, extend the exact FOLIO-style reading layer with a compositional
semantic view that can represent entities, events, roles, modifiers,
complements, identity, and definiteness while retaining exact evidence and
provenance. While parked, the remaining sections record that campaign's
contract and evidence; they are not instructions to mine another increment,
inspect protected data, seal the external release, or build an importer.

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

## Parked resumption gate

Preserve the frozen COGS DEV baseline and PMB candidate. The one permitted PMB
protected standard-test aggregate has been spent: 923 items produced 1 exact,
0 safe partial, 922 declined, and 0 incorrect at 100% projected-edge
precision. The sole protected exact graph was `intransitive-agent`; no second
explicit thematic role and no direct-object-versus-recipient class
transferred. This fails conjunctive entry condition 6, so Phase E remains
blocked.

The independent sibling repository `/Users/louis/Development/semantic-generator`
is at pre-review candidate commit `af93ad0`; its public manifest records release
fingerprint
`b73f2bbd2ac027f2bbfa319b2cb02d3142eac6d5b23af2c0ec6659b2117f7ac2`
and status `pending_review`. No protected bundle is sealed in that manifest.
Human review must occur in the isolated fabrication context, not from inside
RuleKit.

While parked:

- do not rerun or inspect COGS TEST/generalization or PMB standard-test rows,
  identifiers, sentences, graphs, or failures;
- do not tune PMB against the protected aggregate;
- do not inspect protected synthetic plaintext from this repository context;
- do not seal the external candidate or construct a RuleKit importer; and
- do not claim that Phase E is unblocked.

On explicit resumption, first confirm review completion, sealing, verification,
licence, release fingerprint, and encryption manifests. Then preregister the
one-way RuleKit import/adapter boundary and evaluation thresholds before
running any candidate against encrypted development. Protected test remains a
separate deliberate one-look decision.

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
uv run pytest -n 4 --dist=worksteal
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

- **Generate** — seeded premise-rule specimens and human review;
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
FOLIO reader mining into a resumed semantic-projection campaign.
