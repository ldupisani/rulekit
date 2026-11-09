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
  cut: {senses: [verb], verb: {lemma: cut, past_participle: true}}
```

An entry declares `senses`; it may also declare `plural` (one surface or a
list), surface `number`, verb `lemma`, `anaphoric_form`, `lexical_phrase`,
and `notes`. Morphological fields are sense-scoped: a plural requires a noun
sense, verb information requires a verb sense, and an anaphoric form requires
a pronoun sense.

`verb.past_participle: true` explicitly admits a participial surface whose
form is invariant or irregular. Runtime matching and generation share this
check alongside productive participles; no word exceptions belong in Python.

`verb.number` overrides surface `number` for explicit verb agreement and
generation. This permits a noun/verb homograph to keep its singular noun
reading while declaring a plural finite verb form. Both paths use
`LexiconEntry.number_for_sense`; an unmarked past form remains number-neutral.

`verb.finite: false` declares a non-finite surface whose shape alone is
insufficient evidence. Reading, expense learning and generation share the
same form check; a merged perfect auxiliary keeps its own finite surface.

`lexical_phrase: true` marks an indivisible multiword noun, adjective or adverb with
exactly that one sense. It is not a general replacement for compositional
compound parsing.

Declared hyphenated noun plurals retain their canonical identity and require
the source hyphen boundaries. An explicit non-noun entry for the plural
surface keeps its own readings without suppressing the noun paradigm;
agreement follows the selected reading.

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

For semantic noun categories, list the singular lemma and declare its plural
forms once in the lexicon. A declaration such as `snail: {senses: [noun],
plural: snails}` makes both forms members of any category containing `snail`,
including ancestor categories and nominal `includes` unions. Category
enumeration exposes both forms too; repeating `snails` in each membership
list is unnecessary. Irregular and alternative plurals use the same declared
mapping; the engine does not guess them from spelling.

Noun morphology does not grant verb, name, or other grammatical categories.
Use rule-slot `number` constraints for singular/plural agreement. Genuine
plural-only nouns can carry `number: plural` without an invented singular.
A grammatical surface set may still explicitly select a plural marker such
as `times`; this does not classify its singular as that marker.

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

Shared English vocabulary has one alphabetized owner in
[`core-english/lexicon/core.yaml`](../packs/core-english/lexicon/core.yaml).
Its noun and verb roles, attributes, and compatibility belong beside their
category definitions, rather than in alphabetic category files or a benchmark
pack. A word may have several justified roles: a container may also be an
ownable object and an interior location. Neither lexical recognition nor a
basic noun sense grants every arithmetic role. Ambiguous people/device heads
do not become personal-pronoun antecedents merely because one reading is human.
An animate-subject constraint also does not grant a verb a quantitative use;
quantitative predicates require their own category membership.
The [shared vocabulary tests](../tests/test_shared_vocabulary_categories.py)
check these distinctions and ordinary inflections. Core English also compiles
without optional science or benchmark packs.

Use hierarchy for an “is a” relation. Use compatibility tables for “can fill
this role.” Neither statement asserts an event or affiliation in the text.

Noun categories may declare `disjoint_with: [other_category]` to prove that
their members cannot belong to the other family. The compiler makes this
relation symmetric and carries it through descendants and included families.
Unknown or non-noun targets, overlapping families, and shared members fail
compilation, including contradictions introduced by extension packs. Missing
membership and sibling categories alone never establish separation. Consumers
opt into this proof explicitly; it does not close a category's vocabulary.

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
| `formulas` | Word → typed derived attributes; explicit word definitions override category defaults |
| `parameter_bindings` | Word → declared parameter equalities |
| `formula_units` | Physical basis → canonical unit and optional conversion category |
| `formula_constants` | Shared identifier → finite numeric constant |
| `property_aliases` | Authored quantity phrase → property identifier |
| `part_counts` | Part word → dimension key |

### Scalar and derived category properties

Category definitions may declare `attrs`, `formulas`, and `parameter_bindings`.
Parent definitions flow downward to members and subclasses; a union's included
families do not copy their properties onto the union or its other members.
The most specific category definition wins. Equal unrelated definitions retain
all sources; conflicting unrelated definitions require an explicit resolution.
Word-level definitions override defaults. Duplicate conflicting word definitions
across documents fail compilation instead of depending on pack order.

A formula declares `inputs`, `expr`, `result_dimension`, and optional numeric
`constants` (a local numeric map or a list of names from `formula_constants`).
An input dimension is a basis name or an exponent map; `{}` is
dimensionless. Expressions support numeric constants, named inputs, arithmetic
`+`, `-`, `*`, `/`, constant powers, and unary signs. Inputs and constants must
all be used. Addition requires equal dimensions; products and powers compose
dimensions, and the result must match the declared dimension.

An input may name another derived property or a scalar default. Compilation
rejects dependency cycles, binding cycles, incompatible dimensions, and unsafe
expressions. Runtime evaluation uses the shared arithmetic logger, rejects
missing or unused measurements, and checks declared equalities. Unit-bearing
values convert through the existing conversion tables and `formula_units`.
For example, `length: {unit: meter, category: length_unit}` confines conversion
paths to the declared family, including intermediate units. A legacy string
such as `length: meter` permits only identity or direct declared conversions;
it cannot infer a physical family from an ambiguous conversion graph.
Area and volume conversions raise the scale factor to the appropriate power.
Bare mathematical inputs use the declared canonical basis. Geometry questions
cannot mix stated units with omitted units or select incompatible output units.

`parameter_bindings` maps equal parameter roles to a common name. The shared
square class maps rectangle length and width to `side`; the cube class does the
same for three cuboid axes. These relationships are declared knowledge and
must never follow from generic shape membership alone. Spatial dimension is
a separate scalar: a solid's surface area has squared-length dimension while
its volume has cubed-length dimension. An absent formula is unknown, not zero.

Noun properties follow declared plural morphology; grammatical metadata on a
mixed-sense word does not become a property of its noun plural. Effective
values, formula definitions, and origins are available through Registry's
property accessors. SourceIndex retains editable declarations for authoring.

Implementation: [property compiler](../src/rulekit/data/properties.py),
[property evaluator](../src/rulekit/kernel/properties.py),
[shared geometry definitions](../packs/core-english/categories/geometry.yaml),
and [executable contracts](../tests/test_category_properties.py).

Ask generation may declare `property_bindings` with `subject`, `property`,
and an ordered `parameters` list of `{slot, component}` records. A component
is `identity` or `qualifier`. The generator reads the same compiled property
contract to choose compatible quantities and leaf parameters and omit unused
optional parameter groups. `requires_committed_answer` keeps each generated
property question subject to ordinary solve verification. Reader coverage can
include output-unit variants even when generation omits those optional slots.

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

An atomic numeric compound takes its own declared value during lexical
condensation, independently of its components' numeric meanings. This does
not reinterpret an ordinary counted noun as a fraction.

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
| `bindings` | Slot → need → actual target slot, for complete grammatical constructions |
| `references` | Referring slot → actual target slot |
| `emits` | Typed facts with slot templates or numeric expressions |
| `overlapping` | Opt into adjacent overlapping match windows |
| `question_assumption` | Explicitly allow the supported detached conditional promotion |
| `independent_clause` | Opt a fact-emitting sentence reader into complete-clause coordination and comma-boundary recovery; both sides still require full grammar coverage |
| `generation, generation_context, generation_where` | Authoring controls, described below |

`satisfies` records structural satisfaction, not a referent. `references`
retains a real target and checks its anaphoric compatibility. They cannot both
claim the same slot's `refers` need. Neither permits arbitrary missing evidence
to be ignored. `bindings: {each: {collection: holders}}` preserves the actual
counted collection for a floating distributive. Its source need and both scalar
slots are checked at compile time; a bound need cannot also use `satisfies`.

An emitted fact is not automatically an answer. Consumers must use compatible
evidence and guards must permit the commitment. Empty `emits` can preserve
a complete nonnumeric frame without inventing quantities, but consuming
values is not a general escape hatch for unsupported numeric prose.

Descriptor compatibility can opt into `when_declared: true`. In that mode,
an undeclared descriptor leaves the construction open, while a descriptor with
a declared category boundary must license the bound noun. This allows shared
location frames to restrict carrier objects without declaring proximity or
surface prepositions interchangeable.

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
| `all_qualifiers` | Require every retained modifier to belong to `qualifier_cat`, including nested qualifiers |
| `referential, bare_reference_category, determinerless_category` | Referential completeness and explicit exceptions |
| `bare, class_only, standalone, single_word` | Additional shape restrictions |
| `integer, value_positive, value_min, value_max` | Numeric restrictions; `value_positive` requires a finite value strictly above zero |
| `fraction_within_whole, word_fraction_within_whole, fraction_positive` | Part-of-whole and positivity contracts |
| `bare_form, finite_form, present_participle, past_participle` | Verb morphology |
| `span, span_blocks, span_blocks_counted` | Bounded span capture and barriers |
| `enumeration_cat` | Span-only: an exact singleton or conjunctive list of heads in this category |
| `enumeration_counted` | Require one counted nominal per enumeration member; per-item emission retains its value and reference |
| `enumeration_qualified` | Permit explicit modifiers on an uncounted, category-validated list; per-item emission retains the full reference |
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

`modifier_host_compatible` defaults to a noun host. With `host_type: verb`,
it requires an object slot and a declared verb–preposition–object licence in
`adposition_roles`. Matching, learning and generation use the same table;
an omitted optional phrase is neutral. This prevents a valid location phrase
from attaching to a verb that cannot take that relationship. An explicit
`nominal_host` slot also permits a declared nominal modifier (such as a
book's topic); it does not make otherwise unlicensed PPs optional. A separate
noun-host predicate can enforce attachment restrictions on both readings.

`bound_requires_category` can include `bound_cat` to activate the restriction
only for controller words in that category. For example, third-person
possessives can restrict a nearby relationship owner while first- and
second-person possessives remain anchored to the speaker or addressee.

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

`activity_account_evidence` extends `batch_evidence` with `reporting_period`
and `prior_period`, each retaining its full structured reference. Keep these
separate from the measured activity duration and from continuation/correction
markers. A qualified period preserves its grain and relative offset; its head
alone cannot distinguish this week from the previous week.

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

`disambiguates: [slot, ...]` lets the selected construction commit the listed
category slots to their category's root sense. Each slot must be unique,
category-gated, and a single analyzed unit. Selection is recorded in the
reader trace and removes obligations belonging only to discarded senses.
It does not select senses in unmatched prose or discharge an unrelated need.
Read-phase sentence rules use the same field and validation contract. Statistical
inquiries select their aggregate and frequency senses only inside a complete
inquiry frame.
The material-area ask uses this for the interrogative amount word, remainder
adjective, and square-unit modifier in a complete area question.

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

A generated premise's `target_status` reports a structural match;
`clean_reading` additionally requires strict generation, no collisions, no
reading deficiencies and no lexical relaxations. It is not a human judgment
of meaning. Pinned premise reviews with machine gaps remain in need of
attention even when their grammatical verdict is valid, and cannot supply
clean reusable evidence. Review history remains unchanged.

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
- Legacy `geometry` entries have `shape, quantity, expr`. Shared shape formulas
  now belong to typed category properties; contradictory legacy declarations
  fail compilation. Legacy entries without a unit contract remain unitless.
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
validation evidence in tests and benchmark snapshots, and report check results
with the change.

Scoped proportional calculations also retain their population and role evidence:

- `population_evidence` retains member type, owner, indexed collection,
  assessment and boundary independently. Education contributes cohort vocabulary;
  the same partition rules cover people and products in other indexed collections.
  A numeric collection index is an identifier, not a population count. A
  `scale_label` reads a categorical assessment boundary; numeric boundaries remain
  raw operands and are audited in both the premise and question.
  A strict threshold supports its identical strict query or its inclusive
  opposite at the same boundary; the kernel does not invent a grade ordering.
  Unindexed shares reuse ordinary ownership counts for the same owner and member
  type. An indexed share still requires an explicitly matching indexed total.
  An explicit named owner of a plural subject or its preceding indexed collection
  remains a discourse candidate after condensation. Later personal and possessive
  pronouns can refer to that owner; competing names remain ambiguous.
- An `enumeration_cat` span can require `enumeration_min_members` (default 1).
  Joint totals require at least two named participants, leaving individual
  earning statements to the ordinary quantity machinery.
- Joint earnings retain the named participants, total, absolute share references,
  and relative share dependencies. Existing `relation` facts can supply pure
  fractional or multiplicative edges. Cycles, conflicting definitions, foreign
  participants, and shares exceeding the total decline.
- Itemized accounts use `expenditure` facts with `basis: quote`, preserving
  quantity, unit price or whole-lot price, and original numeric positions. Shared
  pricing resolves these operands; shared resource arithmetic totals the charges.
  Quotes establish costs, not paid transactions or cash balances. Objects and
  packages use purchase categories. A shared activity/location introduction
  covers work and dining; domain activities and venues enter through subcategories.
  Relative price quotes are per item or package unless explicitly marked as a
  line total. Equal allocation requires a payer count and an equal-split clause.
  `charge_record_noun` supplies bill, invoice, statement, check, tab and account
  as contextual names for those charges. This category does not equate their
  other senses or infer a balance, payment, or settlement from the noun alone.
- `specification_evidence` separates application context, reference input/output ratio,
  explicit ratio reuse, and output demand. A recipe, formula, method, prescription,
  procedure, blueprint or plan supplies no ratio by its name alone. An explicit
  "requires N inputs for every M outputs" or "uses N inputs per M outputs"
  specification and its matching adoption determine a scalable input requirement.
  Counted goods and measured materials share the same rate/unit machinery.
  Observed output/input relationships and population-based demands use shared
  grammar in the same file. Culinary products, activities and portion measures
  enter through subcategories; the rules contain no culinary category gates. The same substance and unit can occur
  in both roles without becoming the same quantity. Unit conversion stays within
  each role. Source-local numeric auditing explicitly includes measured modifiers
  such as an `8-ounce` serving; ordinary consumers retain their existing policy.
- Located yield facts retain the collector, item, station, and site. Ordered site
  references resolve against the order of the two introduced sites; each rate
  uses its own population. A missing comparison standard is licensed only when
  precisely two compatible collectors are established.

- Threshold purchase discounts combine ordinary unit prices (`price` facts) with
  an explicit quantity threshold. Marginal policies reduce only excess units;
  whole-purchase policies reduce all units once the threshold is exceeded.
  Counts, threshold, buyer, item and discount scope must agree. Per-unit asks
  return a uniform paid price; mixed prices require an explicit average ask.
  Zero-unit purchases have no paid per-unit price.
- Comparative purchase budgets reuse `expenditure` pricing and resource totals.
  A stated pair price covers the pair. A requested item list must identify the
  complete referenced basket before a multiplier is applied. Category references
  use `purchase_collection_noun` and the shared `purchase_collection_contains`
  check: every priced item must belong to the requested category. Named group
  intentions can introduce the same collection; they do not create purchases.
  Clothes and ingredients use YAML category membership, while generic goods
  use the existing ownable-object gate. Mixed baskets outside the referenced
  category decline; partial-category subtotals are not inferred.
- Nested collection partitions retain outer counts, inner units per container,
  and `batch_evidence.content_count` per inner unit. An explicit remainder uses
  the total minus the counted partitions. Equal sharing preserves fractional
  results instead of silently rounding physical items.
- Event totals reuse bounded affine-sequence arithmetic from an initial term.
  An initial event plus N further events means N+1 terms. Nominal references
  remain source evidence and do not contribute additional terms.
- Named budget allocations retain fractional destinations and an explicit
  remainder. Every fraction applies to the original, independently bound
  `resource_allocation`; a different owner, overlapping destinations or an
  over-allocation declines. Ordinary accounting establishes the opening balance.


### Personal roles at locations

`arithmetic/rules/role-locations.yaml` owns the general “person is a role at
place [in area]” family. It replaces the education-only budget context and
the separate logic bridge reader. `person`, `role_location` and
`geographic_area` supply the semantic domains; schools remain an organization
subcategory alongside commercial organizations, and ordinary spatial places
are also eligible. These gates describe the stated relationship, not employment.

The rules emit qualified `Membership` for the role and an exact `Atom` for
the complete role/location phrase. Indefinite locations retain their article
in the predicate key and set `indef_obj`, preventing inheritance from a class
restricted to a particular place. A stated area remains in that key rather
than being silently discarded. Existing declared role refinements remain
responsible for deriving a broader role, such as teacher from head teacher.


Review-driven semantic boundaries also apply to generated premises:

- Benefit receipt uses its own verb category; buying a benefit is not inferred.
  Discount fractions are bounded to one whole at the grammar boundary.
- Acquisition and disposal use category-owned verb/theme frames. The acquired
  batch consumer rechecks these frames after resolving pronouns and
  question-local removal, using the same declared item categories.
- Situated roles exclude kinship terms and use organizations or declared
  activity sites. Ordinary role nouns require an article; office
  titles have separate article-free variants of the same template.
- Inventory opening templates bind one intrinsic attribute family (color,
  size, or ripeness), and require distinct subtypes. Sequence and remainder
  descriptors are not independent inventory classes. The overlap linter
  respects modifier-category gates as well as head-noun gates.

Event progressions retain the source fraction in `event-percent-step` evidence;
`25% more` becomes a recurrence factor of `1 + 0.25` only in the consumer, after
source-number auditing. A forecast verb or future modal marks a projection.
Projected terms may be fractional and are summed without rounding; unmarked
actual counts must remain whole numbers. Initial, recurring, and queried effects
must agree through the existing object-gated `context_synonyms` contract. The
structural-event vocabulary groups collapse and destruction only for declared
event-result objects, rather than making them unrestricted verb synonyms.

Explicit `.optional` string placeholders work both alone and inside a larger
string. Omitting an ordinary required placeholder remains an error.
