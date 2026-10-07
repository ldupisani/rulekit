# RuleKit YAML reference

This guide is for authors editing projects and packs in the RuleKit Designer
or a text editor. It explains how to express language knowledge and how to
check it. The [architecture](architecture.md) explains the runtime behind it.

The authoritative field definitions are the Pydantic models in
`src/rulekit/data/schemas.py`; compilation adds cross-document checks.
The Designer's **YAML reference → Live schemas** view exposes those models
from the running version, including nested types, defaults and enums. JSON
Schema does not encode every Python validator or runtime restriction: use
Save + validate and a reading/generation round trip as well.

## Contents

- [Files and validation](#files-and-validation)
- [Projects and packs](#projects-and-packs)
- [Lexicon](#lexicon)
- [Categories and relationships](#categories-and-relationships)
- [Numbers and grammatical obligations](#numbers-and-grammatical-obligations)
- [Premise rules](#premise-rules)
- [Match tokens](#match-tokens)
- [Cross-slot predicates](#cross-slot-predicates)
- [Facts and rendering](#facts-and-rendering)
- [Ask rules](#ask-rules)
- [Templates and variants](#templates-and-variants)
- [Generation contracts](#generation-contracts)
- [Synthesis](#synthesis)
- [Units and domain data](#units-and-domain-data)
- [Guard settings and reserved seams](#guard-settings-and-reserved-seams)
- [Authoring and troubleshooting](#authoring-and-troubleshooting)

## Files and validation

Every document is a YAML mapping with a `format: rulekit/<kind>@1` discriminator.
Packs discover YAML recursively; the filename does not determine its meaning.
Use unique mapping keys, explicit stable rule ids, and quoted template strings.
Unknown fields are normally errors, not ignored configuration.

| Format | Main fields | Purpose |
| --- | --- | --- |
| `rulekit/project@1` | `name, packs, suite, datasets, splits, projection` | Select runtime packs and evaluation data |
| `rulekit/pack@1` | `name, version, requires, activation, description` | Pack manifest |
| `rulekit/lexicon@1` | `entries` | Words, senses and morphology |
| `rulekit/categories@1` | `categories, members` and relationship tables | Taxonomy and compatibility |
| `rulekit/numbers@1` | Numeric surface maps | Number/fraction/operator knowledge |
| `rulekit/obligations@1` | `roles` | Grammatical needs |
| `rulekit/rules@1` | `rules, asks, templates, variants, ask_variants` | Reading and question constructions |
| `rulekit/synth@1` | `rules` | Fact joins |
| `rulekit/conversions@1` | `conversions` | Multiplicative unit factors |
| `rulekit/affine-conversions@1` | `scales` | Offset-and-factor conversions |
| `rulekit/formulas@1` | `dimensions, formulas` | Dimension-bound formulas |
| `rulekit/geometry@1` | `formulas` | Shape-bound formulas |
| `rulekit/calendar@1` | `span_units, months` | Calendar data |
| `rulekit/elements@1` | `masses` | Atomic masses |
| `rulekit/contractions@1` | `expansions` | Explicit contractions |
| `rulekit/reference@1` | `tables` | Typed reference records |
| `rulekit/quarantine@1` | `words` | Withheld vocabulary and reasons |
| `rulekit/guards@1` | `guards` | Registered guard settings |
| `rulekit/requirements@1` | `shapes` | Reserved provider requirements |

This inventory is checked against `KIND_MODELS` in tests. Complete field
shapes are available in Live schemas rather than a second handwritten schema.
Fact emissions, synthesis fields, reference rows, and guard settings have
intentional extensibility; acceptance there does not imply that arbitrary
fields have runtime meaning.

## Projects and packs

A project is a directory with `project.yaml`. For example:

```yaml
format: rulekit/project@1
name: authoring-example
packs: [core-english, difg-mined, arithmetic]
```

Named packs resolve in the nearest repository's `packs/` directory.
Relative pack paths resolve from the project. A pack contains `pack.yaml`
and its format-tagged data documents:

```yaml
format: rulekit/pack@1
name: authoring-example
version: 0.1.0
requires: [core-english]
description: Reusable constructions for a domain.
```

`requires` names sibling pack dependencies, loaded recursively. Do not
duplicate base vocabulary to make a pack self-contained. Duplicate or
incompatible declarations can fail loading or compilation.

`suite` points to a curated YAML suite. Answer `datasets` identify Parquet
paths and question/answer columns; `splits` select a source, optional MD5
bucket, and an optional aggregate-only firewall. A `projection` project
instead specifies a COGS/PMB adapter and projection splits. Projection cannot
be combined with answer datasets or a suite.

Project evaluation settings do not grant permission to inspect protected
data. The Designer edits existing loaded pack documents, not project files or
datasets. Pack `activation` is currently a reserved field: loading is eager.

## Lexicon

```yaml
format: rulekit/lexicon@1
entries:
  token: {senses: [noun], plural: tokens}
  sorted: {senses: [verb], verb: {lemma: sort}}
```

An entry declares `senses`; it may also declare `plural` (one surface or a
list), pronoun `number`, verb `lemma`, `anaphoric_form`, `lexical_phrase`,
and `notes`. Morphological fields are sense-scoped: a plural requires a noun
sense, verb information requires a verb sense, and an anaphoric form requires
a pronoun sense.

`lexical_phrase: true` marks an indivisible multiword noun or adverb with
exactly that one sense. It is not a general replacement for compositional
compound parsing.

`anaphoric_form` declares a named `paradigm` and allowed
`referent_numbers`. Reference compatibility and grammatical verb agreement
are different checks. Use this shared contract for pronoun/possessive
relations instead of adding gender-specific word lists to a construction.

Check quarantine before adding migrated vocabulary. A word's presence in a
category does not replace its lexical sense declaration.

## Categories and relationships

### Taxonomy and members

`categories` maps a category name to a definition with one `parent`.
`members` adds lexical surfaces to categories. Descendant membership is
available through ancestors, subject to sense/root validation.

For example, after declaring a noun-sensed `token` in the lexicon, a
category document can classify it like this:

```yaml
format: rulekit/categories@1
categories:
  demo_countable_item: {parent: noun}
members:
  demo_countable_item: [token]
```

This classifies a word; it does not state that a participant owns any tokens.
The same declaration must not duplicate a category already owned by a pack.

Use hierarchy for an “is a” relation. Use compatibility tables for “can fill
this role.” Neither statement asserts an event or affiliation in the text.

### Nominal family composition

Noun-rooted categories can union other nominal families with `includes`:

```yaml
format: rulekit/categories@1
categories:
  demo_person: {parent: noun}
  demo_institution: {parent: noun}
  demo_holder:
    parent: noun
    includes: [demo_person, demo_institution]
```

The union includes members of descendants and additions from extension
packs. It does not import category flags, selectional frames, or a second
parent. Unknown references, non-noun categories, and inclusion/membership
cycles fail compilation. Source explanations retain the original declaration.

Existing reusable families include `person`, `educational_institution`,
`intentional_agent`, `organization`, `geographic_area` and
`production_device`. Current role sets compose them as follows:

| Role | Families |
| --- | --- |
| Student-count holder | People and educational institutions |
| Earning / activity-initiation actor | Intentional agents |
| Production actor | Intentional agents and production devices |
| Allocation recipient | Intentional agents |
| Institutional population holder | Geographic areas and organizations |
| Animal event participant | Existing animal hierarchy |

Core owns `person`; extension packs add vocabulary. Person membership does
not automatically grant personal-pronoun eligibility: `animate` remains a
separate gate. A device is not made a person merely because both may produce
something. Compatibility licences are not inferred teaching, enrollment or
employment. Generation uses the same sets and does not hide unusual permitted
examples through an undocumented typicality filter.

### Category-owned verb frames

Verb categories may declare `selectional_roles`, mapping semantic role names
to noun categories. Children inherit roles and may narrow their targets to
descendants. Optional `selectional_role_numbers` constrain each role to
singular or plural; children cannot contradict inherited requirements.

The following is a fragment from the category model (its referenced
categories must already exist):

```yaml
consumption_quantity_verb:
  parent: lose
  selectional_roles:
    actor: quantity_event_participant
    theme: consumable_quantity_object
eating_quantity_verb:
  parent: consumption_quantity_verb
  selectional_roles:
    theme: edible_quantity_object
```

A rule maps slots to those roles once:

```yaml
verb_roles_compatible:
  verb: verb
  roles: {actor: [who, standard], theme: [item]}
  allow_proper_name: [who, standard]
```

The most-specific applicable frame wins over its ancestor. Sibling frames
are alternatives, but one complete frame must accept every mapped role:
constraints cannot be mixed between senses. Lookup uses the bound surface
and its declared lemma. `frame_categories` optionally restricts the family.
`require_declared_frame: true` rejects a verb with no applicable declared
frame; without it, the historical no-frame path is open.

Proper-name, plural-class and plural-pronoun permissions belong to the rule's
reference policy, not the lexical taxonomy. They do not override a declared
role-number requirement. Keep overlapping independent facets and negative
exclusions explicit rather than recasting them as alternative senses.

### Compatibility tables

These are fields on a `rulekit/categories@1` document:

| Field | Relationship |
| --- | --- |
| `attribute_compatibility` | Descriptor category → noun categories (including adjective, comparative, preposition and nominal routes) |
| `modifier_host_compatibility` | Modifier category → host categories |
| `adverb_verb_compatibility` | Adverb category → verb categories |
| `measure_holder_compatibility` | Measure category → holder categories |
| `partitive_measure_compatibility` | Partitive measure category → substance categories |
| `modifier_attachment_compatibility` | Preposition/object/host category records |
| `adposition_roles` | Role name → one frame or alternative preposition/object/verb frames |
| `subject_role_derivations` | Verb lemma → role and preserved prepositions |
| `context_synonyms` | Named gated surface equivalences |
| `temporal_offsets` | Deictic temporal lemma → numeric offset |
| `attrs` | Word → numeric attributes |
| `part_counts` | Part word → dimension key |

For example, a category-document fragment:

```yaml
measure_holder_compatibility:
  student_quantity_measure: [student_quantity_holder]
```

The corresponding rule uses
`measure_holder_compatible: {measure: item, holders: [who]}`.
Measure ancestors and holder descendants participate; packs can add target
families without changing the rule. With an `attribute` slot, the licence
is restricted by that adjective's compatibility route. This prevents a unit
shared by age and duration from borrowing an age-only holder licence in a
duration comparison. `when_declared` and proper-name permissions are explicit
options; inspect their exact defaults in Live schemas.

### Behavioral flags

`polarity` is +1 or -1 for directional categories.
`interchangeable` means members denote the same underlying measure;
`superordinate` declares an author-vetted exhaustive subtype family.
`coordinated_superordinate` instead admits an open class only under its
explicit coordinated-evidence contract. It cannot coexist with
`superordinate`. `dimension` identifies unit/dimension families for
consumers that opt in. These flags have different purposes; ordinary
membership alone never licenses summing arbitrary siblings.

## Numbers and grammatical obligations

`rulekit/numbers@1` provides `numbers, scales, multipliers, fractions,
fraction_plurals, operators, currencies, percents`. Fraction plurals map back
to their singular fraction form; a plural unit fraction still needs an
explicit count to form a complete value.

`rulekit/obligations@1` maps `roles` to `needs`, an optional subset
`optional`, and per-need `direction` (`left, right, either`). Obligations
belong to analyzed grammar. Do not suppress a missing role merely to obtain
a numeric answer; use an explicit structural rule when the construction
really supplies that role.

## Premise rules

A complete example using existing core-English categories:

```yaml
format: rulekit/rules@1
rules:
  - id: example/holding
    phase: read
    description: One participant holds an explicitly counted item.
    match:
      sentence:
        - {slot: who, type: name, at_start: true}
        - {slot: verb, cat: plain_have_state, finite_form: true}
        - {slot: item, cat: ownable_quantity_object, counted: true}
        - {lit: '.', consume_skipped: true}
    where:
      - number_compatible: [who, verb]
    consumes: [item]
    emits:
      - fact: quantity
        entity: '{who}'
        measure: '{item}'
        value: item
        verb: '{verb}'
```

This is an isolated teaching example, not an instruction to add a duplicate
holding rule to an existing pack. Semantic restrictions appropriate to other
verbs belong in their category-owned frames.

| Field | Meaning |
| --- | --- |
| `id` | Stable public identity; no authored priority |
| `phase` | Use `read`; post-saturation patterns are not scheduled |
| `match.sentence` | Ordered analyzed-unit pattern |
| `where` | Shared semantic/morphological predicates |
| `consumes` | Slots whose numeric values this construction accounts for |
| `satisfies` | Slot → named obligations discharged structurally |
| `references` | Referring slot → actual target slot |
| `emits` | Typed facts with slot templates or numeric expressions |
| `overlapping` | Opt into adjacent overlapping match windows |
| `question_assumption` | Explicitly allow the supported detached conditional promotion |
| `generation, generation_context, generation_where` | Authoring controls, described below |

`satisfies` records structural satisfaction, not a referent. `references`
retains a real target and checks its anaphoric compatibility. They cannot both
claim the same slot's `refers` need. Neither permits arbitrary missing evidence
to be ignored.

An emitted fact is not automatically an answer. Consumers must use compatible
evidence and guards must permit the commitment. Empty `emits` can preserve
a complete nonnumeric frame without inventing quantities, but consuming
values is not a general escape hatch for unsupported numeric prose.

## Match tokens

Use one token form: `lit`, a named `slot`, or an `opt` sequence.
`lit` is a grammatical literal or alternatives; a slot uses a built-in
`type` or a category `cat`. Optional groups contain ordinary tokens.
Tokens match analyzed/condensed units, not raw character spans.

Common built-in types include `number, ordinal, fraction, multiplier, name, entity,
noun, plural, counted, possessed, qualified, verb, auxiliary, pronoun`.
`ordinal` matches a productive numeric ordinal, separately from a cardinal
count. Lexical ordinals remain pack-declared noun modifiers. Numeric ordinal
slots currently have no Designer generation realizer.
Structured types include `point, date, formula`. `proper_name` excludes a
resolved pronoun; `common_noun` is narrower than a general entity.
`bare_plural` and `generic_plural` describe generic class subjects, not
arbitrary definite plural references. Live schemas lists all `SLOT_TYPES`.

| Token fields | Purpose |
| --- | --- |
| `common_noun_cat` | Restrict the common-noun route of an entity slot |
| `counted, uncounted, possessed, qualified, attributive_counted` | Structural noun requirements |
| `qualifier_cat, number` | Qualifier and grammatical-number requirements |
| `referential, bare_reference_category, determinerless_category` | Referential completeness and explicit exceptions |
| `bare, class_only, standalone, single_word` | Additional shape restrictions |
| `integer, value_min, value_max` | Numeric restrictions |
| `fraction_within_whole, word_fraction_within_whole, fraction_positive` | Part-of-whole and positivity contracts |
| `bare_form, finite_form, present_participle, past_participle` | Verb morphology |
| `span, span_blocks, span_blocks_counted` | Bounded span capture and barriers |
| `enumeration_cat` | Span-only: an exact singleton or conjunctive list of heads in this category |
| `at_start` | Anchor the first match token |
| `consume_skipped, blocks_skipped` | Control permitted skipped material |

A `referential` singular common noun generally needs a determiner or other
identity-bearing structure; a proper name does not. `bare_reference_category`
is a pack-owned exception, not permission to accept every bare noun.

`fraction_within_whole` bounds all fraction values to [0, 1].
`word_fraction_within_whole` applies it to word/slash fractions, but exempts
percentage surfaces. `fraction_positive` separately requires a value greater than zero.
Do not impose a part-of-whole upper bound on an unbounded ratio.

Generation-only token options are `generation_bare_reference`,
`generation_all_numbers`, and `generation_explicit_unit_fraction`.
They shape realization without silently narrowing reader acceptance.
Field combinations are validated; a list of field names is not permission
to combine incompatible token forms.

## Cross-slot predicates

Each `where` entry declares one predicate. Slot names must belong to the
construction. Most predicates require specific scalar types or category
roots; compile the pack to validate these contracts.

| Predicates | Use |
| --- | --- |
| `same_lemma, same_surface, same_phrase` | Match lexical, written, or phrase identity |
| `same_number, number_compatible` | Number identity or subject/verb agreement |
| `same_presence, mutually_exclusive` | Coupled or alternative optional branches |
| `distinct, distinct_owner, distinct_from_owner, distinct_measure` | Explicit identity separation |
| `owner_matches` | Possessed argument belongs to the named owner |
| `same_category_membership` | Slots share membership under a declared category |
| `category_contains, category_nonoverlap` | Collection membership / nonoverlapping categories |
| `bound_requires_type, bound_requires_category, bound_rejects_category` | Optional controller conditions a target |
| `bound_requires_form, category_requires_bound` | Morphology or presence depends on a controller |
| `verb_roles_compatible` | Map slots to category-owned complete verb frames |
| `verb_role_compatible` | Legacy conditional facet or negative exclusion |
| `measure_holder_compatible, partitive_compatible` | Apply category-owned measure relationships |
| `attribute_compatible, modifier_host_compatible, adverb_verb_compatible` | Apply modifier relationships |
| `polarity_compatible, proportional_delta_compatible` | Consistent direction and legal proportional magnitude |
| `text_prefix_split` | Declared structural split of a text value |
| `name_count, absent, slot_not_category, preceding_verb_category, unbound` | Specific structural boundaries |

Prefer `verb_roles_compatible` for a coherent positive lexical frame.
`verb_role_compatible` remains appropriate for independent overlapping
facets, negative exclusions, or a construction-specific role mapping that
cannot be represented as a complete frame. Do not duplicate verb/object
vocabulary pairs in every rule.

The example `number_compatible: [who, verb]` checks agreement, not semantic
plausibility. Likewise, being different words is not necessarily evidence
that two participant descriptions denote distinct entities.

## Facts and rendering

`emits` selects a supported `fact` discriminator. Additional fields are
fact-specific, written alongside `fact` (or inside `fields`). The live
`FactEmit` schema enumerates fact kinds but intentionally leaves their
payload open; `kernel/model.py` and the emitter in `kernel/patterns.py`
define each payload's runtime contract.

String templates such as `'{who}'`, `'{item.qualified}'`, or
`'{who.owner}'` render bound identities/attributes. Numeric fields such as
`value: item` read a slot value; arithmetic expressions use the restricted
evaluator, not Python execution. `sign(dir)` reads category polarity.
Not every unit property is a supported template attribute.

`'{people.members}'` emits a tuple of canonical heads from a span with
`enumeration_cat`. The compiler requires that gate; the matcher rejects
mixed-category, modified, counted, and disjunctive lists. Named-holder asks
use the same list grammar and require at least two names.
`'{resource.owner_identity}'` reads a resolved, unmodified owner identity
from the structured reference; unresolved ownership renders empty and must
be rejected by the consumer.

Keep identity and qualifiers in fields supported by the target fact.
Do not encode several meanings into an opaque concatenated string when a
typed field exists. A count of people, an item amount, a goal, a credit limit,
and an actual account entry are different commitments.

Portioned-whole rules retain structured noun references on `batch_evidence`.
Modifiers are composed using ordinary noun grammar and category-owned
compatibility; product variants do not need atomic lexicon entries or alias
families. Later less-specific references may describe the one established
population, while an extra or contradictory modifier declines. Nominal
compounds retain both the modifier's head and its own qualifiers.

Three scoped aggregation facts preserve information that ordinary quantities
cannot express on their own:

- `allocation_group` carries the source, resource, exhaustive named recipients,
  and optional stated recipient count. Its consumer reuses ordinary receipt
  quantities, relations and holder totals.
- `indexed_path_evidence` distinguishes a route's checkpoint population, known
  segment lengths, unknown segment, immediate exit and overall length. A
  residual needs every other segment accounted for; turn direction never
  implies equal lengths or rectangular geometry.
- `measured_component` keeps the participant, material and unit together,
  plus an optional dependency on another material/unit count. The explicit
  component-tally ask adds the requested numerical counts; it does not convert
  unlike physical quantities. Missing references, cycles, repeated components
  and mismatched unit labels decline.

Special emission metadata includes `temporal_perspective`,
`distributive` (quantity/rate), and `container_count` (quantity).
`each` emits per enumeration segment; `options_from` supports the declared
exhaustive disjunction form. These are structural contracts, not arbitrary
looping or templating facilities.

## Ask rules

Asks live under `asks` in a rules document. They match `question`, apply
`where`, and either render `resolves` or declare explicit interpretations:

```yaml
format: rulekit/rules@1
asks:
  - id: example/item-count
    match:
      question:
        - {lit: how, at_start: true}
        - {lit: many}
        - {slot: item, type: plural}
        - {lit: does}
        - {slot: who, type: name}
        - {lit: have}
        - {lit: '?', consume_skipped: true}
    resolves:
      consumer: single-entity
      entity: '{who}'
      measure: '{item}'
```

`resolves` is a normalized query, not an expected answer. Its fields are
defined by the named consumer; values are strings or lists of strings.
Consult an existing ask for that consumer before adding a new surface.
The example is intentionally narrow and does not replace the richer
agreement/role boundaries of production asks.

Exactly one of `resolves` or `interpretations` is required. Alternatives
need a `clarification` prompt and unique interpretation ids, labels, kinds,
and resolutions. `satisfies` can discharge explicitly identified
question-local grammatical roles.

Only one ask is selected. It wins by consumed units, category depth, and a
stable id tie-break. Test near neighbours and malformed suffixes: a valid
prefix must not silently hide a different or nonsensical question.

## Templates and variants

Templates reduce repeated grammatical structure without moving vocabulary
into Python. They are local to one `rulekit/rules@1` document.

```yaml
format: rulekit/rules@1
templates:
  statement-frame:
    parameters:
      opening: []
    rule:
      phase: read
      match:
        sentence:
          - {parameter: opening}
          - {slot: who, type: name}
          - {slot: verb, cat: plain_have_state, finite_form: true}
          - {slot: item, cat: ownable_quantity_object, counted: true}
          - {lit: '.', consume_skipped: true}
      where:
        - number_compatible: [who, verb]
      consumes: [item]
      emits:
        - {fact: quantity, entity: '{who}', measure: '{item}', value: item, verb: '{verb}'}
variants:
  - id: example/plain-frame
    template: statement-frame
  - id: example/additive-frame
    template: statement-frame
    arguments:
      opening: [{lit: also, at_start: true}]
```

A reference `{parameter: name}` replaces a whole YAML value; a list-valued
parameter used in a list is spliced. Dotted paths select values from a mapping.
Arguments are literal YAML, not executable expressions or recursive template
references. Unknown/unused parameters, invalid expanded rules, and duplicate
ids fail validation. A template cannot own an id: variants own public ids.

Use `ask_variants` for ask bodies with `match.question` and `resolves`
or interpretations. Premise variants may override their description. Runtime
sees ordinary expanded rules; source navigation retains the authored template
and variant.

## Generation contracts

Generation is authoring support, not another grammar. Matching, generation
availability, filler pruning, and the final round trip share the relevant
slot and predicate contracts. A supported rule can still generate a bad
sentence: exposing that defect is one reason for human review.

### Premises

| `generation` | Meaning |
| --- | --- |
| `premise` | Default reviewable premise |
| `contextual` | Reviewable with declared surrounding discourse |
| `reader-only` | Recognition support, not offered as a generated premise |
| `safety` | Intercepts invalid/incomplete prose to prevent false fallbacks |

`generation: contextual` requires `generation_context`, containing
`before`/`after` lists of `sentence` token sequences with optional
`where` constraints. `target_identity_links` maps context slots to target
slots' semantic identity. It does not copy their counts or surface wording.
`required_fact_counts` checks the composed reading;
`target_commas_after` supplies declared surface punctuation.

`generation_where` shapes generated forms only. Put semantic rejection
boundaries in ordinary `where`; do not hide an invalid reader commitment by
making the generator stop showing it.

### Asks and evidence

An ask's `generation` is a mapping, not the premise enum:

| Field | Purpose |
| --- | --- |
| `context_required, context_strategy` | Require `evidence` or `conditional` context |
| `evidence_rules` | Ordinary premise rule ids and slot → normalized-query-path bindings |
| `slot_sources` | Project reference groups or reference years |
| `slot_categories` | Narrow generated vocabulary while preserving reader structure |
| `validated_slot_bindings` | Bind generated slots from normalized reviewed fact fields |
| `validated_source_bindings` | Preserve reviewed source-slot wording, including tense/modality |
| `omit_slots` | Do not realize optional rejection-only capture branches |
| `requires_committed_answer` | Require answer evidence for the declared generation contract |

Context-required asks must declare the strategy and evidence rules together.
Bindings contain no prewritten answer. `evidence` keeps the question intact;
`conditional` embeds an ordinary premise in the supported conditional form.
The full result must still solve through the intended ask.

“Smallest answerable” means bounded search for an irreducible generated
premise set: removing a returned premise must break answerability. It is not
a proof of global minimum length and can report that no supported plan was
found. “Answerable from validated premises” uses included clean human-positive
evidence and rechecks it against the current runtime; an unrelated valid
review is not sufficient for every ask.

Project generation fixtures and append-only review/exploration records are
authoring data, not `rulekit/*@1` runtime pack documents. Do not copy review
JSONL into a pack.

## Synthesis

```yaml
format: rulekit/synth@1
rules:
  - id: example/transitive-order
    when:
      - {fact: before, earlier: A, later: B}
      - {fact: before, earlier: B, later: C}
    unless:
      - {fact: before, earlier: A, later: C}
    emit:
      - {fact: before, earlier: A, later: C}
```

Fact patterns bind variables and join shared bindings. `unless` checks the
current store; it is not general natural-language negation. Saturation adds
facts until a fixed point or the round limit. It does not retract earlier
consequences if later evidence appears. Use only fact fields and literals
supported by the synthesis runtime; arbitrary YAML keys are not new fact
semantics.

## Units and domain data

Multiplicative conversions use `from, to, factor`:

```yaml
format: rulekit/conversions@1
conversions:
  - {from: metre, to: centimetre, factor: 100}
```

Use `substance` for a conversion valid only for that material.
`scope: cadence` separates conventional rate projection from general exact
elapsed time. Do not let a substance-specific density or a conventional
calendar factor become a global equivalence.

Affine `scales` use `from, to, offset, factor` and compute
`to_value = (from_value + offset) * factor`. They are separate from
multiplicative conversions.

- `formulas` declares `dimensions` and entries with `quantity, expr, scope`
  (`question` or `document`).
- `geometry` entries have `shape, quantity, expr`.
- `calendar` supplies `span_units` and optional month numbers.
- `elements` supplies atomic `masses`.
- `contractions` supplies explicit `expansions`.
- `reference` tables declare `name, key, attributes, rows`; attribute
  metadata distinguishes numeric units, year indexing and group keys.
  The optional DuckDB resolver must be available for its aggregation path.
- `quarantine` maps words to reasons and optional tags; it is a vocabulary
  exclusion contract, not a list to work around.

Consult Live schemas for exact nesting and required types. Constants and
domain relationships belong here, not in consumer word lists.

## Guard settings and reserved seams

`rulekit/guards@1` maps registered guard names to settings including
`enabled`. Adding an unknown setting cannot implement a guard. Disabling
a safety check to make one example answer is not a grammar fix.

These schema surfaces are reserved or incomplete:

- Pack `activation`: eager loading, no dynamic activation.
- `requirements.shapes`: compiled, no provider loop.
- `phase: post-saturation`: accepted, not scheduled.
- Multi-sentence pattern sequences: accepted, not executed.
- A declared `overrides` field is not an author-controlled rule-priority
  mechanism; use ordinary structural specificity and collision inspection.

Schema validity, registry compilation, matcher execution, generation
availability, and an answer commitment are separate checks.

## Authoring and troubleshooting

1. Choose the layer: vocabulary/category extension, sentence construction,
   derivation, or ask surface. Reuse an existing contract before adding one.
2. Edit the owning pack document. In the Designer, **YAML reference** opens
   this guide without replacing the current editor or losing unsaved text.
3. Save + validate. Inspect source-linked errors and lint warnings.
4. Read invented positive and negative examples. Inspect matched rules,
   consumed values, facts, collisions, gaps, and the consumer's decline reason.
5. Generate the target where supported, capture human review, and retest the
   exact pinned text after edits. Test ambiguity and nonsensical neighbours.
6. Run proportionate synthetic tests, curated regression and relevant lint.
   Shared kernel changes warrant broader regression checks. Protected TEST
   remains a separately authorized action.

Typical commands from a development checkout:

```sh
.venv/bin/rulekit --project projects/curated lint
.venv/bin/rulekit --project projects/curated solve "Aven has 4 apples. How many apples does Aven have?" --trace
.venv/bin/rulekit --project projects/curated bench --slice suite
.venv/bin/python -m pytest tests/test_category_inclusions.py
```

| Symptom | First check |
| --- | --- |
| Word is unknown | Loaded packs, lexical sense, inflection, quarantine |
| Valid word cannot fill a slot | Type/category route, morphology, role frame, all `where` predicates |
| Rule matches but no answer | Fact payload, identity/scope, ask query and consumer requirements |
| Competing facts disappear | Collision and specificity evidence; do not add priority |
| Generator is blocked | Availability explanation, missing filler or unsupported structure |
| Generated ask has no scenario | Evidence plan support, required context, search budget |
| Validated-premise mode has few results | Included clean reviews and compatible fact/source bindings |
| Live schema differs from edited code | Running server version; a Python change needs a user-managed restart |

Maintain this guide when a YAML contract changes. Update architecture only
when responsibility or data flow changes; keep per-question history and
validation counts in the handoff, focused examples, or campaign records.
