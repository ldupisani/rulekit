# The scratch inference roadmap — from copular syllogisms to set logic

This is the "designed inference frontier" the FOLIO campaign closure named as
the only legitimate way back to logic coverage (`docs/negative-results.md` →
"The FOLIO buyer is UNWIDENABLE"). Everything here lives in `projects/scratch`
at zero blast radius: no benchmark project loads `./packs/logic`, folio stays
the 0/0 safety gate, and folio TEST remains governed by the closure rules.

## Ground rules (inherited, non-negotiable)

- **Extend the vetted layer, never bridge the permissive one.** Atoms are
  minted only by rules that opt in construction-by-construction (`at_start`,
  whole-span capture, fail-closed variants). The generic fold's facts never
  reach a verdict — the if-antecedent leak and passive junk are PINNED as
  tests (`test_if_antecedent_cannot_reach_a_verdict`,
  `test_passive_junk_cannot_reach_a_verdict`).
- **Phrase keys are exact; entailments are MATERIALIZED, never matched
  loosely.** New set-logic capability = new sound entailment-materializing
  rules, each category-gated where English is not uniformly monotone.
- **Monotonicity decides where decomposition may apply**: Atom.pred and
  Quantified.pred are upward-monotone (stripping is sound); Quantified.cls is
  downward-monotone (stripping WIDENS the universal — forbidden, everywhere,
  forever). Negative facts never decompose.
- **Every stage is one revertible commit** with synthetic contracts (the
  tests are the specification), the full six-corpus gate, and folio dev-train
  re-measured (DEV looks are free; the measuring stick is commits + null
  controls).

## Where we are (done)

| piece | commit |
|---|---|
| v2 kernel half resurrected; pack scoped to scratch | `ed45811` |
| `_canonical_phrase` Fiedler fix (admitting a word must never loosen a key) | `ed45811` |
| Qualified-compound membership (fold): loose-match + negated-compound fixes, intersective split | `ce90fa5` |
| **A. Intersective decomposition of atoms** — shared `intersective_split` contract, top-level-nominal-only, composes with instantiation | `4d57816` |
| **Stage 1: copular if-then conditionals** — Conditional fact + 3-antecedent synth; someone-form emits `quantified`; fail-closed variants pinned | `3afae6f` |
| **Stage 2.1: restrictive relative clauses drop** (structural, marker adjacent to lead) | `60b0e76` |
| **Stage 2.2: PP restrictions drop** (quantifier-guarded — 'a friend of no person' never drops) + the fold's negated-PP suppression | `87e4b2e` |
| **Stage 2.3: conjunctive predicates assert both conjuncts** — `conjunctive_marker` category gate ('or' is ALSO conjunction-sensed; a sense gate split disjunctions — caught by test before ship) | `1813bfe` |
| **Stage 2.4: Quantified.pred / Conditional.then_pred decompose** — `_DECOMPOSABLE_FIELDS`, upward-monotone consequents only, cls pinned unstrippable | `fd088a2` |
| **Stage 3: disjunction, case analysis, exclusivity** — Disjunction/QuantifiedDisjunction facts; exclusivity MEASURED (bare 'or' = ∨, 'either…or' = ⊕, the James minimal pair); 6 synths (case analysis + disjunctive syllogism sound under both readings; XOR-elimination exclusive-only); disjunctive-conclusion asks + consumer | this commit |

Folio dev-train after Stage 3: still **1 commit / 0 wrong / 494** (declines
359→369: or-surfaces the disjunction rules cannot soundly read are now
REFUSED and fragment-vetoed instead of opaquely swallowed). The honest
blocker: FOLIO's real disjunctive premises are mostly VERBAL ("have chat
features or video features"), and verbal reading is the explicitly-deferred
family (its own increment + its own look, per the v1 revert record). The
copular set-logic core is COMPLETE and contract-proven; folio yield now
waits on Stage 4 morphology + the verbal frontier, not on more copular
machinery.

## Stage 1 — copular conditionals (the largest measured premise family) — DONE

83 of the 170 copular-conclusion folio dev-train stories contain an if-then
premise (the ladder simulation's histogram). Shapes, narrowest first:

1. `If a X is [not] P, then it is [not] Q` → a `conditional` fact
   (antecedent preds → consequent pred, polarity); instantiation is an
   n-antecedent synth rule — the engine already runs multi-antecedent Horn
   clauses (`synth/universal-instantiation` is 2-antecedent).
2. `If someone/something is P, then they are Q` → degenerate 1-antecedent
   form (equals a universal; emit `quantified` directly).
3. Negated ANTECEDENTS stay unread initially (¬P → Q licenses nothing
   without case analysis — that is Stage 3's machinery).

Soundness notes settled in advance:
- The extraction rule anchors `{lit: if, at_start}` and captures the WHOLE
  construction or nothing — an unmatched variant ("unless", "only if",
  "provided that") leaves the sentence unread, which is monotone-safe.
- The moment SOME conditionals are readable, decide the fragment-guard
  question: 'if' currently carries no truth-scoping sense (safe only because
  nothing reads if-sentences). Reading part of the family must not let
  half-read conditional sentences slip — the whole-construction match plus
  sentence-level unread-monotonicity covers it; write the argument down in
  the rules header when landing.

## Stage 2 — decomposition siblings (more intersection-elimination) — DONE

Each is the A pattern in a different construction, each its own increment:

1. **Relative-clause split**: `atom(x, 'conductor who specialized in Y')`
   additionally yields `atom(x, 'conductor')` — restrictive relatives are
   intersective. Needs the split at the UNIT level (the span knows where the
   relative pronoun sits), never string surgery.
2. **PP restrictions**: `'student at yale'` ⊨ `'student'` — positive only
   (the fold's negative-with-PP laxity is a known latent hole; fix its
   emission the same way the compound negative was fixed).
3. **Conjunctive predicates**: "X is a singer and an actor" → both atoms.
   The conjunction is consumed structurally, which also relaxes the
   fragment guard's 'and' veto for exactly this shape.
4. **Synth-derived atoms + Quantified.pred**: decomposition currently runs
   only at rule emission; a chained/instantiated atom with a compound pred
   ("czech mammal") is not decomposed (coverage gap, not unsoundness).
   Extend the same helper into saturate.py's emission path.

## Stage 3 — disjunction, case analysis, exclusivity ("branching") — DONE

The FOLIO witness (TikTok story) requires all three; 75 dev-train stories
carry disjunctive premises:

1. A `disjunction` fact kind: `disj(x, P, Q)` from "X is [either] a P or a
   Q" (ground) and `quantified_disj(C, P, Q)` from "All C have P or Q".
   Read whole-or-nothing; 'or'/'either' likely need a truth-scoping sense
   the day this lands, so an unread disjunction vetoes instead of being
   swallowed into a phrase key.
2. **Case analysis** (3-antecedent synth): `disj(x,P,Q) ∧ P⊆R ∧ Q⊆R ⊢
   x∈R`.
3. **Exclusivity**: FOLIO's 'either…or' golds are EXCLUSIVE (the banked
   TikTok item: "either has chat features or is a computer program" is
   False because BOTH hold). XOR-elimination derives NEGATIVES:
   `xor(x,P,Q) ∧ x∈P ⊢ x∉Q`. Decide inclusive-vs-exclusive per surface
   form from DEV gold evidence BEFORE emitting either — a wrong default
   manufactures confident-wrongs in both directions.

## Stage 4 — quantifier morphology and existentials — DONE

Landed: 'any' universals (via the opt-in `consume_skipped` lit flag — 'any'
is an article, auto-skipped, so no ordinary lit could see it; 'the'/'a'
still never match, pinned), 'each' universals, "Everyone who is P is [not]
Q", and 'some' existentials (Existential fact; premises consume the
quantifier, relaxing the fragment veto by capability; conclusions answered
by echo, query-time WITNESS, or a refuting NEGATIVE universal — no
existential import from positive universals).

**Folio dev-train after Stage 4: 2 commits — 1 correct + 1 vs a
FOL-VERIFIED POISONED GOLD (never chase it).** Story 266 / example 710:
"All CD players are delicate mechanisms. No delicate mechanisms are
suitable toys for children. ⊢ Some CD players are suitable toys?" — our
'no' (chain + ∀¬-refutes-∃) is entailed by the item's OWN premises-FOL,
and its conclusion-FOL (∃ two distinct suitable CD-player toys) is
likewise refuted by it; the 'Uncertain' label contradicts the dataset's
own formalization. The ASDiv London/Blair precedent: a documented
annotation error, counted neither as a wrong nor as coverage.

- `any`-universals ("Any choral conductor is a musician") — 'any' carries
  the article sense, so the rule needs its own reading; v2's named-next list.
- 'Each' universals; "Everyone who is P is Q" (pronoun-quantified copular).
- 'Some' existentials: `exis(P, Q)` facts + ∃-introduction
  (`atom(e,P) ∧ atom(e,Q) ⊢ "some P are Q"`), which also relaxes the
  fragment guard's 'some' veto for read sentences.

## Stage 6 — the VERBAL frontier — DONE (re-landed from v1, hazards designed out)

Ground-verbal, verbal universals, verbal embedded asks, and the
existential-verbal form ("Is it true that A dog eats apples?" — witness
search via the Stage 4 consumer, `consume_skipped` stopping the article
skip). The three v1 hazards each have a structural fix, all pinned:
'be'-twin -> `nonstate_verb` slot type (fold AND lemma checked against
`state` — the lemma-only draft let 'is' through); participle missplit ->
the verbal pred span blocks verb-sensed words, so participial-cls
sentences fall to the copular rule ("All books sold by the school are
cheap" reads cls='book sell by school'); the arithmetic clash ->
`span_blocks_counted` keeps merged counted nouns the fold's ('Tom bought
3 apples' keeps its Quantity; bare dates ride in verbal spans).

Folio dev-train: commits unchanged (1 + the poisoned gold) but the READING
moved: declines 362->322, undetermined 124->170 — 40+ more stories reach
the consumer. Conversion needs paraphrase bridging (verbal keys are
echo-exact).

**⚠ The "next levers" this file named after Stage 6 were MEASURED AT ZERO
(2026-07-17) — do not build them.** Participial restriction drops and
verbal PP drops bridge **0 of the 170 undetermined** items: no conclusion
key is a word-prefix of any premise atom pred for the right entity,
directly or through one instantiation step (prefix covers ANY number of
tail drops, so this is not a depth artifact). The measured gap taxonomy
instead (scratchpad classifier, both directions checked):

| class | n | what it needs |
|---|---|---|
| entity-atoms-unrelated | 52 | mostly honest Uncertain golds + deep inference |
| entity-raw-other | 37 | constructions the pack cannot read (participial, passives, bare plurals) |
| paraphrase-gap (≥50% overlap, no containment) | 28 | multi-premise composition ("attended the University of Edinburgh" + "Edinburgh is in the UK" ⊢ "attended university in the UK") — a frontier |
| entity-in-raw-or | 23 | conjunctive disjuncts ("either P and Q, or ¬P and R") — Stage 3 extension |
| entity-absent | 13 | definite descriptions / anaphora |
| entity-in-raw-if | 10 | conditional forms Stage 1 refuses (negated antecedents etc.) |
| substring-bridge (mid-atom) | 2 | subject-relative predication ("a politician WHO SAT in the House of Commons" ⊢ sat...) — sound but only 2 buyers, one on a corrupt premise |

Also: only **100 of the 170** have verdict golds — the 70 'Uncertain' rows
can never convert (undetermined is a non-commitment BY DESIGN), so every
lever must be priced against the verdict-gold subset.

## Stage 7 — quantified conclusions (2026-07-17) — DONE, and the misbinding it closed

Three commits, each gate-clean and independently revertible:
1. `974dea2` **qualified_render**: a merged NAME rendered TWICE in every
   phrase key ('Emmet Building' -> 'work at emmet emmet building') — four
   call sites shared the words[:-1]+[lemma] idiom, one helper owns it now.
   SYMMETRIC (premise and query keys share the renderer), so no verdict
   test could see it; the new tests pin FACT KEYS. Folio item-level NEUTRAL.
2. `4211b2f` **capitalized quantifiers never name**: the FOLIO wrapper
   preserves the conclusion's sentence-initial capital, so 'No plants are
   mushrooms' read as name('No') + verb('plants') — three stacked
   misreadings behind one undetermined. Structural sense exemption in
   senses.py beside the timeperiod one. Trade measured first: ONE real
   quantifier-headed name in all seven DEV corpora ('All Goods Available
   store', declines before and after) vs 78 wrapper-capitalized quantifier
   conclusions in folio dev-train (32 No / 23 Some / 23 All).
3. `b313980` **all/no conclusion asks + universal-verdict consumer** over
   the saturated Quantified closure; 'no' only from a counterexample
   witness — NO existential import in either direction (saturation
   instantiates the witness whenever the class is nonempty, so the sound
   path is complete). "All X are not Y" stays unread (scope ambiguity).

Folio dev-train after Stage 7: commits unchanged (1 + the poisoned gold);
301 no-ask / 179 undetermined — 9 quantified conclusions moved from
opaque decline to the new consumer, honestly undetermined. **Conversion
blockers, in buying order** (each is its own increment; measure first):
- **Bare-plural universal premises**: "Mushrooms are fungi" is FOLIO's ∀
  (its FOL says so) and is UNREAD — worse, sentence-initial unknown
  'Mushrooms' name-annotates. This blocks the one derivable witness item
  ("No plants are fungi. Mushrooms are fungi. ⊢ No plants are mushrooms"
  gold True) and is the gate on the next blocker:
- **The negative-chain synth**: quantified(M,F,+) ∧ quantified(P,F,-) ⊢
  quantified(P,M,-) — sound FOL, but its ONLY measured buyer needs bare
  plurals read first. An unbought enabler until then; do not land alone.
- **Verbal universal conclusions** ("All species of Ambiortus live in
  Mongolia") — the Stage 6 ask family, conclusion side.
- **Unknown-plural morphology**: 'barkers' (unknown) stays verbatim while
  the premise's 'a barker' is singular — echo-exact keys miss. A general
  lever (affects every span key), price it as one.

## Stage 8 — bare-plural universals + negative chain (2026-07-17) — DONE

`a0f98b9`. "Mushrooms are fungi" read as ∀ (FOLIO's FOL convention; 57
dev-train premises + 19 negated, measured). Four premise rules, subject =
ONE unit: new slot types `bare_plural` (plural noun, no owner/qualifier/
COUNT — "Three dogs are pets" passed the first test round and was caught
by an adversarial probe; the tests are the specification, but only of what
they phrase) and `proper_name` (name sense only — `name` admits resolved
pronouns, and "They are dogs" must never mint a generic). Definite
subjects refused via the pack's `definite_article` category. The -not
variants are unambiguous ∀¬ (no quantifier to out-scope, unlike the
dropped "All X are not Y"). synth/negative-chain (M⊆F ∧ P∩F=∅ ⊢ P∩M=∅)
landed WITH its buyer: folio dev-train 1 → **2 correct** (+1 SOLVED /
0 BROKE), the exact predicted plants/mushrooms derivation, all four null
controls move. Compound generics ("Guard dogs are protective") stay
unread — a measured coverage hole, not a hazard.

Still open from the Stage 7 blocker list: unknown-plural morphology, the
∀¬-symmetry synth (q(A,B,-) ⊢ q(B,A,-) — sound, pinned as deliberately
unbuilt in test_negative_chain_wrong_direction_stays_open until a buyer is
measured), and bare-plural DISJUNCTIVE premises ("Surprises are either fun
or dreadful" — the qdisj rules' cls is quantifier-led only).

## Stage 8c — tokenizer Unicode + the verbal 'some' conclusion (2026-07-17) — DONE

- `2dd5eb8` **_TOKEN letter class is Unicode**: the ASCII class shredded a
  word at its first diacritic ('Sūduva' -> 's' + 'duva', 'Léa' -> 'L' +
  phantom ARTICLE 'a'). Exposure measured first: gsm8k 9 DEV items (all
  decline before AND after), scibench 7, folio 17, zero elsewhere; ASCII
  tokenization pinned byte-identical. This unlocked the Sūduva premises
  (previously ZERO facts) and surfaced Stage 8's second conversion on
  folio dev-HOLDOUT (sports cars / family automobiles via negative-chain,
  null-controlled — first measurement of holdout with the pack).
- `6e20158` **ask/logic-existential-some-verbal**: "Some CLS <verb> P?"
  reusing the Stage 4 consumer's witness path verbatim. Buyer measured
  BEFORE building (the Super Cup item, gold True), converted on landing:
  folio dev-train 2 -> **3 correct** (+1 SOLVED / 0 BROKE), all four null
  controls move. do-support negation pinned unread ('do' is not
  verb-sensed — its own increment).

**Verbal universal conclusion asks (all/no × verbal) were MEASURED AND
DEFERRED, not built**: every unmatched verdict-gold item needs machinery
beyond the ask — Ambiortus/live needs the definite description "the ONLY
known species", "All birds swim" (gold False) needs a never-generic
premise ("A hawk never swims") + refutation of ∀ by ∃¬, Turing/sergeants/
business-owner need relative-clause predication or list-membership
distribution. An ask family with zero convertible buyers is an unbought
enabler; the misbinding Stage 7 closed does not recur here (these
conclusions currently just decline). Re-measure after the witness-side
machinery lands.

## Stage 8d — unknown-plural morphology, the `.singular` fold (2026-07-18) — DONE

**The "measured at zero" claim below was true of the WRONG JOIN.** The zero
measured naive-singularization over conclusion↔premise key pairs; the buyer
lives in the premise↔premise join that measurement never covered — an
unknown-plural universal instantiating against the SINGULAR copular atom
("Tyga is a rapper" + "Rappers are not opera singers" ⊢ no). Re-measured
over the 95 consumer-reached verdict-gold declines: **3 conversions to
gold, 0 manufactured wrongs** ([386] Tyga needs only this; [426]
Lewandowski additionally needs a verbal conditional read — its derivation
now exists but the fragment guard correctly vetoes on the unread
"If a player leaves a team…"; [185] Douglas Adams additionally needs the
relative-clause drop to fire on an unknown-word lead).

**What landed:** a `.singular` TEMPLATE ATTR (patterns.py `_naive_singular`
+ `_slot_value`/`_canonical_phrase`/`atom_variants`) — naive plural→singular
for words the lexicon cannot fold, opt-in per rule. Applied to the whole
PLURAL-AGREEING key family, premises AND asks together (17 templates:
all/every/no/any/each-ARE universals, bare-plural ×4, some-are ±not,
qdisj-all-are ×2, and the all-are/no-are/some-are conclusion asks) — the
-is/-was variants are singular constructions and never fold (their keys
join ground atom preds verbatim: the 'lens' hazard). Decomposition sees
through the attr (else Stage 2.4 pred variants silently die on those
rules — caught at design time). Known lemmas byte-identical, names keep
surface keys, -ss/short words guarded; all pinned
(test_bare_plural_universals.py, 8 new tests; the two verbatim-'wugs' pins
updated as the deliberate contract change).

**Gates:** pytest 1397; all 8 benchmark slices snapshot-diffed NEUTRAL;
folio-with-logic dev-train **6 → 7 correct** (+1 SOLVED / 0 BROKE — the
Tyga buyer, provenance `synth/universal-instantiation`), dev-holdout
1/0 unchanged (the sports-cars conversion survives under folded keys —
the fold is symmetric); four live null controls move (absent entity,
absent class, cut premise ×2).

**What it un-blocks next (each was one-piece-away in the walk):**
- **[426]**: a VERBAL conditional premise read ("If a player leaves a
  team they no longer play for that team") — the instantiation chain is
  ready; only the fragment veto stands.
- **[185]+[186]**: the relative-clause drop's lead gate — but see the
  BANKED measurement below; the drop alone is NOT enough.

## Stage 8e — the titular-name stack (2026-07-18) — DONE; the banked drop RE-LANDED with its buyer

**Folio-with-logic dev-train 7 → 8 correct (+1 SOLVED / 0 BROKE — [185]
Douglas Adams/writer), holdout unchanged, all 8 benchmark slices
snapshot-diffed NEUTRAL, pytest 1409 (+12 pins), three null controls
move (absent subject, absent pred, cut universal).** Three pieces, one
stack, one commit:

1. **The titular name merge** (condense.py): NAME + partitive + NAME →
   ONE name ("Salmon of Doubt", "University of Edinburgh"). Gated on the
   `partitive` CATEGORY (core-english already held 'of' as its member —
   kernel references the category name only). The left part may also be a
   mid-sentence CAPITALIZED known word (the pairwise "Tall Tuna" signal —
   'Salmon' is a lexicon fish and never falls back to the name sense), but
   NEVER sentence-initial ("Members of Pappy's have starred" is a plural
   description). Head features come from the NAME side (inheriting the
   left noun's sense left the title unable to bind any name slot —
   measured live before the fix).
2. **The article capitalization exemption** (senses.py): the mid-sentence
   naming rule now exempts article-sensed words, beside the Stage 7
   quantifier exemption and for the same wrapper reason — "Is it true
   that The <Title> is …" embeds the sentence-initial capital, and a
   name-annotated 'The' pairwise-merged into the title while the premise
   side keyed without it: the same text stopped echoing itself (caught by
   this increment's own echo test, not by any corpus). 'The Hague'-style
   names stay symmetric (the article is skippable on both sides).
3. **The unknown-lead relative drop re-landed** (patterns.py, from the
   bank below) — with the titular sentence now READ, the fragment veto
   lifts and the drop + Stage 8d fold convert the buyer.

Next in this story: [186] ("Douglas Adams created innovative ideas") still
needs bare-plural VERBAL universals ("Writers create innovative ideas" —
today a ground atom on entity 'writers'). [426] still needs the verbal
conditional read. The other titular stories ([3]/[4] Blake McFall — needs
identity/aliasing; [6]/[8]/[9] Dickinson — needs coordination or sits on
the run-on corpus defect) keep their own blockers.

## Stage 8f — bare-plural VERBAL universals (2026-07-18) — DONE

**Folio-with-logic dev-train 8 → 9 correct (+1 SOLVED / 0 BROKE — [186],
the Douglas Adams story's second conclusion), holdout unchanged, all 8
slices NEUTRAL, pytest 1416 (+7 pins), both null controls move.**
"Writers create innovative ideas" is FOLIO-FOL's ∀ exactly as the copular
generic is; the Stage 8 subject pair (bare_plural / proper_name, definite
article refused) applied to the Stage 6 verbal reading. The copular pair's
plural-agreeing {lit: are} has no verbal counterpart, so a new opt-in
MatchToken flag **`bare_form`** (fold == lemma, the bare present) is the
structural generic-vs-ground signal: "Mary CREATES ideas" and "Douglas
Adams CREATED the book" stay ground (inflection ≠ bare form), pinned. The
p span deliberately does NOT fold — it must join ask/logic-embedded-
verbal's unfolded span render symmetrically. cls folds (`.singular`).

**⚠ The unknown-lead relative drop was BUILT, MEASURED and REVERTED
(2026-07-18) — an unbought enabler; do not re-land it alone.**
*(RESOLVED same day: re-landed as piece 3 of Stage 8e above, with the
buyer the bank predicted. Kept for the record:)* The change
(accept a SENSELESS lead in `atom_variants` — the decomposable fields are
copular predicate positions, so the construction guarantees a nominal
lead where the lexicon is silent; a verb/adjective/name-sensed lead still
refuses) is SOUND and passed everything: pytest 1397+5, all 8 benchmark
slices snapshot-diffed NEUTRAL, folio-with-logic dev-train AND holdout
**item-level neutral — 0 buyers**. The isolated [185] chain works
("…author who created X" → 'author' → the folded universal → yes), but
the REAL item is fragment-vetoed by a DIFFERENT sentence: "The Salmon of
Doubt is about life experiences AND technology" — the TITULAR multi-word
name ('Salmon of Doubt', lowercase 'of' blocks name-merging) keeps every
copular rule from reading it, and its unread 'and' prices the item (the
S2 lesson: walk the buyer's WHOLE story before sizing a stack — this
walk was done for the stack's first piece and not re-done for the
second). Re-lands in one step WITH the titular-name copular read (or any
future buyer): the diff is one condition + five pinned tests, recorded
in this repo's history at the Stage 8d commit's immediate successor
attempt — recreate from this paragraph.

## The cheap-increment frontier is EXHAUSTED (measured 2026-07-17, three zeros)

Three candidate families were measured after Stage 8c and every one is
DEFERRED with zero convertible buyers — do not build them from this list;
re-measure only after the composition machinery below exists:

1. **Unknown-plural morphology**: naive-singularization of unknown words
   bridges **0** conclusion↔premise key pairs on the entire undetermined
   set (the synthetic 'barkers' witness exists; no real item is blocked on
   exactly that).
2. **Bare-plural disjunctive premises**: 9 items, conclusions are mostly
   compound conditionals or Uncertain golds. No clean class.
3. **Do-support negation** ("Is it true that X does not V ...?"): the
   biggest surface — 29 conclusions, 15 in the simple form — and ZERO
   convert: 7 are 'have' (a STATE verb, excluded from nonstate_verb by
   the be-twin discipline — possession lives in the fold's Predications,
   which the verdict layer deliberately cannot read), 3 are 'live'
   (unknown vocabulary), and the 5 known-nonstate candidates each need
   composition (Ailton plays for Náutico + Náutico is a football club ⊢
   plays for A football club) or sit on corpus defects (the Hoffmann/
   Hoffman TYPO — different entity keys; the Captain America missing-
   period mega-sentence).

**The one recurring blocker across all three (and both Stage 8c
deferrals) is COMPOSITION**: substituting a class or containment fact
into a verbal pred's OBJECT position — 'lives in Manhattan' + 'Manhattan
is in New York City' ⊢ 'lives in New York City'; 'plays for Náutico' +
'Náutico is a football club' ⊢ 'plays for a football club' (∃-intro over
the object). Upward-monotone object substitution is sound where the
embedded relation is containment/membership, but it is a DESIGNED
inference-frontier stage (phrase keys stop being echo-exact; every
derived key needs provenance), not an increment.

**The design is WRITTEN: `composition-design.md`** (2026-07-17). Core
decisions: no string surgery ever (a structured `VerbalRelation` fact
beside the flat atom; segmentation only by match tokens); bridges run at
QUERY time in the consumer; membership bridge sound for any verb,
locative bridge double-gated and Phase 2. It also surfaced a LIVE
measured unsoundness — flat keys drop articles, so "plays for A club"
confidently answers "plays for THE club?" today — fixed first as Phase 0
(`span_blocks_skipped: definite_article`). The stack table shows the
bridge alone converts ~nothing: shortest complete stack is S2
(active↔passive linking + membership bridge, one measured buyer), then
S1 (adds relative-clause predication, the Stage 7 substring-bridge
class). Build in that order; nothing lands without its stack's buyer.

## FOLIO TEST look #3 — SPENT 2026-07-17 (user-directed, below the closure threshold)

**1 correct / 1 wrong / 283 declined of 285** (ledger row 3; the harness
withholds items on TEST — aggregate-only, so nothing was mined). Spent at
6 null-controlled DEV commits, below the closure's ~10–30 precondition,
by explicit user direction. What it says and does not say:

- **Precision vs the last look ROSE (0% → 50%), so the revert rule does
  not trigger** — and this is the first folio TEST look ever to score a
  correct (looks #1–#2: 0/1 each, surfaces reverted).
- **It mostly measured a coin, as the closure predicted.** At ~2 commits
  on a corpus whose verdict golds are near-binary, 1-right-1-wrong is
  consistent with guessing AND with one real capability plus one bad
  item. The information bought is small; the 6 DEV null controls remain
  the real evidence for the stack.
- **The 1 wrong is a standing liability, deliberately undiagnosed.**
  Candidate explanations that cannot be distinguished without mining
  TEST (forbidden): a TEST-side poisoned gold (DEV carries 1 FOL-verified
  annotation error in 494 → ~0.6 expected per 285 — entirely plausible),
  or a real unsoundness no DEV item phrases. Unlike looks #1–#2 the
  machinery now explains every verdict with a provenance reason string,
  so IF a future in-DEV witness of the same shape appears it will be
  attributable.
- **Next look waits for a CLASS**: keep building (S1, locative on
  re-measure) with per-commit null controls; re-look only when the DEV
  commit count is a multiple of what a coin can imitate.

## Stage 8g — the verbal generic conditional, negated-consequent form (2026-07-18) — DONE

**Folio-with-logic dev-train 9 → 10 correct (+1 SOLVED / 0 BROKE — [426]
Lewandowski, a NEW story per look #4's lesson), holdout unchanged, all 8
slices NEUTRAL, pytest 1420 (+4 pins), null controls move.** One YAML
rule, `logic/conditional-verbal-no-longer`: "If a CLS <v> <obj> they no
longer <v2> <rest>" → a flat-key Conditional (polarity false), the Stage 1
someone-form's verbal sibling. Whole-construction or nothing ('they'+'no'+
'longer' are skeleton literals; 'never' variants stay unread and keep
vetoing — pinned). Both spans block verbs, making the parse deterministic.
The buyer's derivation was already complete — the rule's measured effect
is READING the sentence so the fragment guard stops pricing it (the S2
veto-lift precedent, third occurrence). The story's second verdict
conclusion ("plays for Bayern Munchen?", gold False) STAYS DECLINED and
must: the entailment runs through "Bayern IS a team", which no premise
states — a sortal-free instantiation would fail its own null control
(swap 'team'; the answer must move and would not). Do not chase it.

## FOLIO TEST look #4 — SPENT 2026-07-18 (user-directed, at the band's lower edge)

**1 correct / 1 wrong / 283 declined of 285 — precision 0.5, aggregates
IDENTICAL to look #3** (ledger row 4; aggregate-only, nothing mined).
Spent at ~10 null-controlled DEV conversions (9 dev-train + 1 holdout),
the closure band's lower edge, by explicit user direction. What it says:

- **Precision held (0.5 → 0.5) — no revert triggers**; Stages 8d/8e/8f
  all survive their look.
- **The three dev-train conversions transferred ZERO new TEST items.**
  Identical aggregates cannot prove the same items scored (aggregate-only),
  but there is no evidence of movement. Consistent with the closure's
  long-tail prediction: conversions are nearly story-specific (the Douglas
  Adams story bought 2 of this run's 3), so per-increment TEST transfer is
  thin. The general pieces (the `.singular` fold, titular merge,
  `bare_form` generics) are real but TEST's story distribution does not
  phrase them within one-stack reach.
- **The standing 1 wrong persists** — still undiagnosed by rule
  (TEST poisoned gold ~0.6 expected per 285 remains the leading
  hypothesis; a stable unsoundness is not excluded).
- **Next look: not before the next ~10 conversions**, and prefer
  conversions from DIFFERENT stories — same-story stacking (2 of 3 this
  round) buys DEV count without buying transfer.

## Stage 5 — the gate back to FOLIO (only if/when wanted)

**Precondition 1 is BUILT** (the indefinite-existential gate): every
name-subject slot in the logic pack + arithmetic's ask/is-membership carries
`blocks_skipped: indefinite_article` (REUSING core-english's existing
category — same a/an-vs-the distinction, minted for generic unit prices).
The kernel flag checks the token's PHYSICAL predecessor, not the match
attempt's own skip walk — match_all floats, and a retry starting after the
article would otherwise never see it. Premise side ("A Kliner is a spy"
mints nothing) and ask side ("...that A Kliner is a spy?" refuses) both
pinned; 'the' passes (definite reference).

Preconditions from the closure, all still binding:
1. **The indefinite-article gate FIRST** (the one real hazard the campaign
   probes found; design banked in negative-results §3: split 'a/an' to an
   `indefinite-article` sense kept skippable + an opt-in flag failing a
   match when a named-sense unit was skipped immediately before a token).
2. Re-run the ladder measurement with the real machinery: folio dev-train
   commits, EVERY commit null-controlled (swap subject and predicate for
   absent ones; the answer must move).
3. A folio TEST look only at ~10–30 null-controlled DEV commits — a look
   must measure a class, not a coin. One look per landed increment,
   commit-ordered, revert on any precision drop. Nothing here is exempt
   from `docs/methodology.md`.

## Known open holes (tracked, not forgotten)

- The fold's NEGATIVE Membership with post-head restrictions ("Bob is not a
  student at Yale" → ¬student) — same class as the fixed negated-compound,
  one construction over. Harmless below the verdict layer; fix with Stage 2's
  PP work.
- Privative/temporal modifiers ("former president", "fake diamond"): the
  repo-wide compound-keeps-head contract accepts head-entailment; the atom
  layer deliberately does NOT emit bare heads (pinned), but the fold's
  Membership does. A `privative` category suppressing head emission is the
  eventual fix if it ever bites.
- difg's logic domain stays out of scope: its yes/no golds are 8-of-8 'Yes'
  (an always-yes engine aces it — the null-control lesson).

## Stage 9a — the verbal universal's restrictor folds like its copular twin (2026-07-18) — DONE

**Folio-with-logic dev-train 10 → 11 correct (+1 SOLVED / 0 BROKE — [12]
Tom/Lawton Park, a NEW story per look #4's transfer lesson), holdout
unchanged, all 8 slices NEUTRAL, pytest 1425 (+5 pins).** One slot in one
rule: `logic/universal-verbal-all` emitted `{cls}` while its copular twin
`universal-copular-all-are` has emitted `{cls.singular}` since Stage 8d.
So "All CITIZENS of Lawton Park use the zip code 98199" keyed a class no
ground fact could name — every ground fact naming it is singular ("Tom is
a CITIZEN of Lawton Park"). The derivation was already complete; the two
keys never met.

Not a widening — the Stage 8d invariant applied consistently. 'every'/
'each' keep a verbatim restrictor and are PINNED that way: they take a
SINGULAR restrictor, so folding would truncate an s-final singular
('every species' → 'specie'). Null controls move on all four swaps.

## Stage 9b — 'neither' can no longer hide a negation in a phrase key — DONE

**All 8 slices NEUTRAL, zero outcome AND zero reason moves, pytest 1429.**
This file's header says `span_blocks: negation` goes EVERYWHERE, because a
swallowed negation is invisible to every consumer. 'neither' walked through
it: a difg-mined ADJECTIVE in no category, so no span_blocks entry could
see it. "Tom is neither a Merriam's wild turkey nor a Rio Grande wild
turkey" minted Atom(tom, "neither ... nor ...", polarity=**TRUE**) — a
positive fact asserting the negation of its own sentence. New
`neither_marker` category (exact mirror of `either_marker`) lets the
copular pred span REFUSE the construction. Dormant hazard, now pinned: a
conclusion of the same shape would have echo-matched that key.

**DELIBERATELY SPLIT — the De Morgan READER is BANKED, NOT LANDED.** "X is
neither A nor B" → two NEGATIVE atoms (¬A ∧ ¬B) is written, sound, and the
one disjunction surface needing no exclusivity measurement (unlike the
Stage 3 'or' pair). It buys ZERO dev-train items, so it waits for a buyer
(the `_TOKEN` precedent). Recreate: mirror `logic/disj-ground-either` with
`{lit: neither}` / `{lit: nor}`, both spans blocking `neither_marker`, and
emit two `atom` facts with `polarity: false`. Its likeliest first buyer is
[400] (Tom / six wild turkey types), which ALSO needs the "There are six
types: A, B, C, D, E, and F" enumeration read as a disjunction — two
pieces, land them together.

## Stage 9c — `bare_form` fails closed on the -s agreement suffix — DONE

**All 8 slices NEUTRAL, pytest 1433 (+4 pins). A PRECISION fix: it mints
FEWER universals, never more.** `bare_form` (Stage 8f) is the whole
generic-vs-ground signal, and it reads `fold == lemma` as "uninflected" —
which is only ever as good as the lemma data. **71 s-final verbs in the
lexicon are their own lemma** ('lives', 'leaves', 'agrees', 'consists',
...), so the most inflected form there is passed the bare-form test:
"Rochelle lives in Europe" minted `Quantified(cls='rochelle', pred='lives
in europe')` — a UNIVERSAL over a class, from a ground sentence about one
named individual.

The fix tests the SUFFIX as well and fails closed. An English bare form
ending in a single 's' is essentially nonexistent — the real ones double it
or sit on a Latin stem ('pass', 'discuss', 'possess', 'focus', 'bus'), all
excluded. **Chosen over the lexicon route deliberately:** adding lemma
mappings for the 71 verbs is "more correct" but rewrites fact KEYS across
all seven corpora ('lives in europe' → 'live in europe'), so every existing
join could shift. The kernel guard is precision-only with zero key churn,
and it makes the lexicon fix SAFE to do later (with the mapping in place,
`fold != lemma` refuses on the first test anyway).

The junk universal was latent, not live — nothing in DEV is a 'rochelle' —
so the pin is on the CONSEQUENCE, not just the fact
(`test_a_universal_from_a_ground_sentence_cannot_be_instantiated`).

## The convertible pool is 314, not 483 (measured 2026-07-18)

dev-train declines by gold kind: **169 'Uncertain' items are `text` golds
and can NEVER score correct** (an `undetermined` verdict scores declined
against them — this is the trap negative-results records, and it cuts both
ways: they are not opportunities, only wrong-hazards). The real convertible
pool is **314** (137 false-gold + 177 true-gold declines). Quote 314, not
483, when sizing any future campaign.

## Three general fixes measured at ZERO buyers (banked, do not rebuild blind)

Each is real, each is correct, none is landed — re-measure only after new
stacks land, and land each WITH its first buyer:

1. **`_naive_singular` truncates '-se'/'-ce'/'-ze' nouns.** It strips 'es'
   when `word[-3] in "sxz"`, but 'diseases' and 'glasses' share that
   character while only one is an '-es' plural — so 'diseases' → 'diseas',
   'houses' → 'hous', and every such key can never join. Testing the STEM
   (`stem.endswith(("ss","x","z","ch","sh"))`) is correct on 15 hand-checked
   forms and regresses only 'buses'/'gases'/'lenses'. **0 dev-train buyers.**
2. **An unknown CamelCase proper noun gets NO SENSE AT ALL.** senses.py
   demands `surface[1:].islower()`, so 'TikTok', 'McFall', 'LinkedIn',
   'YouTube' fall through to `unknown` — every `type: name` slot refuses
   them and no ask shape can read a question about one. Widening to
   "tail is alphabetic and carries a lowercase letter" admits exactly the
   CamelCase class (ALL-CAPS acronyms stay out — unit symbols live there).
   **0 dev-train buyers.**
3. **The De Morgan neither/nor reader** (Stage 9b above).

## Two dev-train items are UNWINNABLE corpus defects — never chase them

- **[7]/[8]/[9] William Dickinson**: the FOLIO source text is MISSING A
  PERIOD after "sat in the House of Commons", fusing two sentences into one
  30-word atom pred. Same class as the Captain America mega-sentence.
- Item **228** remains the FOL-verified POISONED GOLD (the standing 1
  "wrong"; it is the proof the judge works).

## The remaining frontier is INFERENCE, not increments (re-measured 2026-07-18)

All 146 undecided items were ranked by key-distance between the conclusion
and the nearest fact key. Past the top few every one needs a designed
stage, and the same four names keep coming up:

- **locative bridging** — [218] Alfonso: "lives in a place named Galicia"
  + "if someone lives in Galicia they live in Spain or Poland" + "Spain is
  in Europe" ⊢ lives in Europe. Needs the deferred locative bridge AND the
  verb-lemma half of the 9c defect ('lives in europe' never joins 'live in
  europe' until the lexicon carries the mapping).
- **n-way disjunctive elimination** — [400] Tom/turkeys (six types, five
  refuted).
- **modus tollens over a universal + entity aliasing** — [99]/[100] Islip:
  needs 'Islip' ≡ 'Islip Speedway' (the same identity machinery the Blake
  McFall items want).
- **reductio / case analysis** — the F/T pairs, already the named S4
  frontier.

The honest read: **Stage 9a bought one item and three other general fixes
bought zero.** The cheap-increment frontier really is exhausted; the next
DEV conversions come from `composition-design.md`'s S2 stack or from S4,
not from more one-slot rules.

## Stage 9d — the reduced relative drops to its head — DONE (76810e1)

**folio-with-logic dev-train 12 (+1/0, the Chevrolet story — a NEW story
per the look-4 policy), all eight benchmark slices byte-identical, pytest
1782.** Two pieces, found by probing the matcher over the 76
"no logic fact decides it" declines (the near frontier — conclusion side
already reads):

- `atom_variants`' tail drop covers the participial postmodifier: "a van
  produced by Chevrolet" IS a van, the same entailment as an overt
  'who'/'that'. Guards structural: 3sg-finite single-s suffix refuses
  (9c precedent), quantifier guard verbatim (a participle is non-finite),
  negatives never decompose. Stage 7's "participial levers measured at
  ZERO" was scoped to atom-pred PREFIX joins on the then-current reader —
  the buyer's premise minted no droppable atom at all until now.
- `logic/qdisj-bare-plural-restricted-either`: the banked bare-plural
  disjunctive premise, landed WITH its first buyer as the RESTRICTED
  form (restrictor verbatim inside the cls key — downward-monotone,
  never dropped). Effect is READING (fragment-guard veto-lift, the 8g
  precedent's 4th occurrence).
- Bycatch: `_TYPE_SENSES` gained `bare_plural` (the nonstate_verb linter
  blind spot, one type over; {lit: all} was reported against a slot no
  quantifier binds). Pinned both directions in tests/test_lint.py.

## Stage 9e — the stated alias — DONE (398e61e)

**folio-with-logic dev-train 13 (+1/0, the Edwin/Ted Smith story — second
new story), pytest 1790.** New `Alias` fact kind + `logic/alias-known-as`
+ two declarative copy synths (both directions, both polarities — identity
transfers denials too). Narrow: proper_name slots only, definite-article
gate refuses epithets ("known as THE Governess"), negated surface never
matches (lit adjacency). Name-shortening ('Islip'≡'Islip Speedway') is a
DIFFERENT mechanism — an inference, not a stated premise — still unbuilt.
⚠ MATCHER LESSON (pinned): a rule whose final slot is a single unit loses
to a sibling whose SPAN swallows the trailing period — strict-superset
subsumption at admit_rule_results. The alias rule claims the '.' via an
opt consume_skipped token to tie. Check this on ANY new non-span-final
rule beside a span rule.

## Running count after 9e: 13 dev-train + 1 holdout conversions

Look #5 wants ~10 conversions PAST look #4's ten, from different stories
— i.e. around 20-21 total; we are at 13+1. Next levers by measured price
(all from the 9d survey of the 76 near-frontier declines):

- **Brian Winter [277]** — 'was appointed as X' → atom(brian, X): an
  'as'-complement reading plus a temporal-PP tail drop ('after his
  retirement' — the PP branch already drops, the 'appointed as' segment
  is the new piece). 2 pieces, 1-2 items.
- **Islip [100]/[101]** — modus tollens over a restricted verbal
  universal + disjunctive syllogism (the Disjunction fact and both DS
  synths ALREADY EXIST — the missing piece is reading "Speedways that
  are still being used have races held at them" and the ¬races premise,
  both 'have'-headed = the state-verb exclusion to walk carefully).
- **[400] turkeys** — the banked De Morgan neither/nor reader + the
  "There are six types: A, B, ..." enumeration-as-disjunction + n-way
  elimination. Two pieces land together per the 9b bank note.

## Stage 9f — the appointive passive — DONE (490a02c)

**folio-with-logic dev-train 14 (+1/0, the Brian Winter story — third new
story), pytest 1797.** Three pieces, each forced by walking the buyer's
whole story: the `appointive_verb`-gated passive rule ("was appointed as
X" ⊨ is an X; resultative members ONLY, 'regarded/described' must never
join), the lead-nominal RUN extension in atom_variants (an unmerged
'referee observer' now reaches the PP drop; additive by construction),
and `logic/existential-some-verbal` (the verbal 'Some' premise — reading,
veto-lift). ⚠ THE SUBSUMPTION TRAP GENERALIZED: a non-span rule beside a
greedy-span sibling must claim EVERY skippable the sibling's span
swallows — the trailing period (9e) AND any mid-sentence article (9f, opt
consume_skipped alternation [a, an, the]). Check both on any new rule
that shares a surface with the ground-copular family.

## Running count after 9f: 14 dev-train + 1 holdout (look #5 at ~20-21)

## Stage 9g — the typed enumeration + the De Morgan reader — DONE (d66a78c)

**folio-with-logic dev-train 15 (+1/0, the wild-turkey story — fourth new
story), pytest 1803.** The 9b bank paid out exactly as written: the De
Morgan neither/nor reader landed WITH the buyer whose story also needed
the enumeration. New kernel piece: `schemas.FactEmit.each` — per-item
emission over an enumeration span ({item} reserved binding, segments
split at commas/conjunctions, structural only). The enumeration rule is
gated on `enumeration_type_noun` ('type' only) so possessive
enumerations ("districts of RUSSIA") stay unread rather than misread.
Exhaustiveness is NOT captured; [400] (the gold-true Ocellated
elimination) still needs the n-way disjunction stage and correctly stays
declined. The 9b pin was updated to its intended invariant (no POSITIVE
atom, no marker in a key) — its empty-store form was the pre-reader
snapshot.

## Running count after 9g: 15 dev-train + 1 holdout (look #5 at ~20-21)

Remaining multi-item near stories all need designed inference stages:
[400] n-way elimination over the (now-read) enumeration; Islip MT+DS
(blocked on speedway(islip) — no premise states it; needs
name-shortening identity, a REJECTED-for-now inference); [128/129]
XOR-conditional reductio; [144/145] do-support negation VR + negative
restrictor refutation; [96/97] modal swamp. The single-item tail is 50
stories of one-off shapes.

## Stage 9h — the exhaustive counted enumeration + n-way elimination — DONE (18fad9e)

**folio-with-logic dev-train 16 (+1/0, [400] — the wild-turkey story's
gold-TRUE item, the first SECOND item from an already-converted story),
all nine benchmark slices NEUTRAL, pytest 1812.** The designed stage the
9g note reserved, in three pieces plus a prerequisite tokenizer fix:

- **Prerequisite (6b2ba94)**: U+2019 was outside the tokenizer's
  apostrophe class and silently DROPPED — "Gould’s" (curly, the
  enumeration sentence) and "Gould's" (straight, the refutation) minted
  different fact keys, so two of Tom's five refutations could never
  join. The fold normalizes ’ -> ' beside .lower(); surfaces stay
  verbatim. Found by dumping the fact store, not by reading rules.
- **`EnumeratedDisjunction`** (model.py): exhaustive n-way class
  disjunction, INCLUSIVE only — the numeral licenses exhaustiveness
  ("there are SIX" + six listed = the list is the whole class), never
  pairwise exclusivity. Keyed by cls alone: disagreeing enumerations
  quarantine -> decline.
- **`FactEmit.options_from`** (schemas + patterns.py): whole-list
  emission gated on stated count == segment count; mismatch or countless
  emits NOTHING (fail closed — a partial list claims nothing). Options
  render via the 9g `.singular` path so keys join the per-item
  universals and the ground atoms.
- **`synth/enumeration-elimination`** (saturate plugin — n-ary is
  inexpressible in the fixed-arity YAML synths): stated positive member
  + all options but exactly one refuted by explicit negatives ⊢ the
  last. Guards pinned in test_logic_verdict.py: no membership -> nothing
  (Joey control); any positive option -> decided (inclusive); >1 open ->
  nothing; a QUARANTINED option atom taints the entity (both sides of a
  contradiction vanish from store.facts, so the option reads as merely
  open to a naive elimination — and the conflict machinery declines the
  item outright anyway).

## Running count after 9h: 16 dev-train + 1 holdout (look #5 at ~20-21)

## Stage 9i — the XOR-conditional reductio — DONE (ea1a266)

**folio-with-logic dev-train 18 (+2/0, [128/129] — the Bubbles gold-false
AND gold-true pair, one story), all nine benchmark slices NEUTRAL, pytest
1823. The S4 assumption-based frontier is OPEN.** The key design fact: the
derivation is LINEAR — no case-splitting tableau needed. Assume goldfish;
the subset chain gives fish; the ∀¬ universal instantiates ¬bird; MODUS
TOLLENS (new synth, the contrapositive of universal-instantiation) closes
¬osprey from osprey⊆bird; the exactly-one antecedent fires ¬fish;
collision. Four pieces:

- `logic/universal-indefinite-copular` ("A carp is a fish" = generic ∀;
  SINGULAR-agreeing so keys render PLAIN, the 8d symmetry discipline;
  negated form deliberately unread).
- `synth/modus-tollens` (positive universals only; REUSABLE — the Islip
  [100/101] MT half now exists).
- `model.DisjunctiveConditional` + reader + fire synths: (A ⊕ B) → ¬C,
  fired ONLY at exactly-one established (sound under ⊕ AND ∨); one true +
  other undecided fires NOTHING (Stage 3's exclusivity measurement).
  ⚠ The fire synths carry NO `unless` ON PURPOSE: the collision IS the
  reductio's contradiction signal; an unless would suppress it. In main
  saturation the same collision = genuinely contradictory premises =
  quarantine -> decline, correct.
- The reductio engine (consumers/logic_verdict.py): an undecided verdict
  atom is assumed each way in a throwaway store copy + fresh log,
  re-saturated; quarantine = hypothesis refuted = negation holds. Both
  ways refuted -> commit nothing. ⚠ NO reductio under a definite-
  description question (q_defcom): the Phase 0 gate refuses indefinite
  atoms in the direct lookup, and the hypothesis would collide with those
  refused atoms and answer through the back door — caught by
  test_article_compatibility, NOT by any corpus. The corpora are a
  sample; the tests are the specification (that memory's third firing).

## Running count after 9i: 18 dev-train + 1 holdout (look #5 at ~20-21)

## Stage 9j — the name-identity stack — DONE (fc60a2d)

**folio-with-logic dev-train 20 (+2/0, [100/101] — the Islip
demolished/still-used pair), all nine benchmark slices NEUTRAL, pytest
1833.** The stage 9e deferred ("design it as its own stage or not at
all"), and the 9i modus tollens was indeed half of it. Four pieces + the
existing DS synths:

- `logic/conditional-restricted-plural-have-at` + `logic/ground-do-not-
  have-at`: the restricted stative-'have' universal and its do-support
  denial — a modus-tollens PAIR by construction: both key 'have {q}'
  through the same render path, and the anaphoric PP ('at them'/'at it')
  is consumed but NEVER keyed (its number differs between the pair;
  keying it would unjoin them).
- `synth/name-prefix-alias` (plugin): name-shortening identity, gated on
  both names being FACT SUBJECTS and the long extension being UNIQUE.
  The 9e Alias copy synths do the transfer.
- `synth/name-head-sortal` (plugin): a ≥2-word, partitive-free name
  declares its head's sort ONLY when the story already quantifies over
  that head (join-driven gate — 'The Salmon of Doubt' stays sortless).
- `synth/conditional-modus-tollens`: then-positive conditionals only.

[99] (the temporal-existential "demolition derby somewhere that has
since been demolished") correctly stays declined — it needs event/time
machinery no stage has.

## Running count after 9j: 20 dev-train + 1 holdout — AT the look-#5 band (~20-21). Ask the user.

## FOLIO TEST look #5 SPENT (2026-07-19, user-directed at 20+1 — the band's edge)

**1 correct / 1 wrong / 283 declined of 285 — aggregates IDENTICAL to
looks #3 and #4 (ledger row 5, fingerprint 7d4af7f7…).** Precision 0.5
HELD: no revert trigger; every stage stays landed. But the transfer
result is the headline, and it is now measured TWICE: the look-4 policy
demanded ~10 more conversions from different stories before looking
again; 9 landed (9f–9j, EIGHT distinct stories, including three designed
inference stages — elimination, reductio, identity), and they
transferred ZERO TEST items. The 1 correct and 1 wrong are the same
stable items as looks #3–#4.

The honest reading: dev-train conversions are story-specific in a
stronger sense than "same story" — the designed machinery is general,
but a TEST conversion needs an entire STORY STACK (every premise reader
+ the inference shape + the ask) to line up, and at 285 items the
overlap rate with any 20-story dev sample is ~0. TEST movement will not
come from more single-story conversions; it would need breadth-first
premise-reader coverage (the 311-item convertible pool's common blocker
classes), which is a different campaign with a different cost curve.
Do NOT schedule look #6 off conversion count alone.

## Phase A — breadth-first premise-reader baseline (2026-07-20)

Phase A of `docs/delphi-learnings-plan.md` is complete. It is measurement
only: no rule, consumer, corpus, snapshot, or TEST state changed. The
machine-readable evidence is `folio-blocker-baseline.json`; it contains only
DEV IDs/labels and aggregates, never copied TEST data.

### The current pool is 305 raw / 302 actionable, not 314 or 311

The 314 figure above was correct at Stage 9c. Stages 9d–9j subsequently
converted nine verdict-gold declines, so the current dev-train pool is
**305**. Three fixed exclusions make the actionable pool **302**:
`72a175580c38` and `b4896190b01e` are the missing-period Dickinson
mega-sentences, and `634b26d06409` needs the explicitly out-of-scope
event/time machinery. The old 311 wording at the end of the look-#5 note had
already subtracted only part of the later movement; it is not a distinct pool.

### Reproducible definitions and fingerprints

- Input: FOLIO's grouped `train` parquet, sliced through the normal harness
  into `dev-train` and `dev-holdout`; only `TypedGold(kind="verdict")` rows.
- Registry: the normal `projects/scratch` registry, which loads the logic
  pack. Each item is solved with tracing off. Direct premise facts are facts
  whose provenance sentence equals that premise's sentence index.
- **Fact-bearing**: a premise emits at least one such direct fact.
- **Fully read**: it is fact-bearing and has no *unconsumed* unknown unit,
  ambiguous unit, unmet obligation, or unread truth-scoping unit. Units
  consumed by a whole-construction logic reader are not blockers merely
  because their lexical sense is otherwise unknown.
- **Stack-ready**: the ask and query are represented, every premise is fully
  read, some fact key overlaps a query entity/predicate, and there is no
  collision, quarantine, ambiguous reading, or clause-split hazard.
  Same-value agreement deduplications remain diagnostic, not blocking.
- Labels are multi-label. There is deliberately **no primary-blocker
  precedence** and no ordering inherited from classifier branch order.
  Exact label definitions and every DEV item ID per label are in the JSON.
- Source commit: `207944dd1b608ca1b8b829e8220e02d9c727e6a3`.
  Logic registry fingerprint: `3b432fed3e47bf4f9773fa1570e956884915a2c7ce8f2d703e2c231b1570760f`.
  Corpus fingerprints: dev-train `5035b9f662b3a888246732397e4d77415703edb77175d6caa1a5b640bbbef697`;
  dev-holdout `6772c96beafd14b45bf63a8ce15c8775cc6002b5e7a5551b36ccaa52ff3cd320`.

The classifier is intentionally throwaway. To regenerate it, use the same
harness loading/slicing path, solve every verdict-gold item with the scratch
registry, derive per-premise facts from provenance plus operative blockers
from `Document.consumed_uids`, then apply the definitions above and the label
definitions in the JSON. The fingerprints must match before comparing totals.

### Baseline

| grouped split | verdict-gold | correct / declined | actionable stories | fact-bearing | fully read | stack-ready items / stories |
|---|---:|---:|---:|---:|---:|---:|
| dev-train | 325 | 20 / 305 | 154 | 1327/1647 (80.57%) | 720/1647 (43.72%) | 14 / 11 |
| dev-holdout | 292 | 1 / 291 | 130 | 1295/1602 (80.84%) | 721/1602 (45.01%) | 6 / 5 |

The actionable dev-train answer shapes are 216 no-ask, 82 represented-but-
undetermined, and 4 other declines. Dev-holdout is 192 / 97 / 2. The roughly
36-point gap between fact-bearing and fully-read coverage is the measured
reason to build premise readers rather than chase additional isolated facts.

Hazard baselines (train / holdout): collision **8 / 12**, quarantine **16 /
24**, ambiguous readings **51 / 33**, clause split **0 / 0**. Agreement
ambiguities are diagnostic-only at **63 / 86**.

### Multi-label construction survey and marginal stack estimate

`gain` means: ask represented and every currently blocked premise carries
that label. It is an optimistic ordering signal, not a promised conversion.

| class | train items / stories / gain items-stories | holdout items / stories / gain items-stories | decision |
|---|---:|---:|---|
| entity-in-raw-or | 17 / 12 / 4-2 | 35 / 24 / 9-6 | first buyer; extend existing Stage 3 machinery |
| entity-raw-other | 9 / 9 / 3-3 | 15 / 11 / 3-3 | survey into real constructions; never ship this catch-all |
| passive | 79 / 36 / 6-4 | 79 / 36 / 6-3 | broad but heuristic; price a narrow passive family |
| relative-clause | 104 / 50 / 2-1 | 91 / 35 / 6-3 | broad but costly/overlapping; split before build |
| entity-in-raw-if | 12 / 10 / 2-2 | 9 / 6 / 0-0 | bank until a two-split buyer appears |
| compound-generic | 9 / 5 / 0-0 | 8 / 4 / 1-1 | cheap candidate, but not yet a two-split stack buyer |
| do-support-negation | 63 / 29 / 0-0 | 41 / 20 / 0-0 | demoted; surface frequency did not buy stack readiness |
| scope-ambiguous universal | 5 / 3 / 0-0 | 5 / 2 / 0-0 | no measured buyer; do not design yet |

Truth-scope vetoes are the dominant cross-cutting symptom: 666 premises / 248
items / 122 stories on train and 614 / 251 / 108 on holdout. They are not one
reader class. Raw coordination, unknown vocabulary, and unmet obligations are
likewise diagnostics that must be resolved through construction-specific
readers, never blanket relaxations. The current strict key-overlap classifier
found no surviving `paraphrase-gap` label; that frontier remains last rather
than inheriting the stale Stage-6 count.

### Shared-kernel reachability inventory

The scratch logic asks already reach six shared, time-scoped consumers:
`logic-verdict` (including reductio), `logic-disjunction-verdict`,
`existential-verdict`, `universal-verdict`, `passive-agent-verdict`, and
`verbal-obj-class-verdict`. The shared saturation registry also always runs
`synth/enumeration-elimination`, `synth/name-prefix-alias`, and
`synth/name-head-sortal`; their effects become reachable when logic-pack facts
are present. Phase D promotion risk therefore includes these shared code paths,
not only the YAML pack.

### Pre-registered look-#6 thresholds

All conditions must hold on **both** grouped splits before asking the user for
look #6:

1. Fully-read coverage improves by at least **8 percentage points**:
   dev-train at least **852/1647 (51.73%)** and dev-holdout at least
   **850/1602 (53.06%)**.
2. Unread truth-scope premise count falls by at least **25%**: dev-train at
   most **499/1647 (30.30%)** and dev-holdout at most **460/1602 (28.71%)**.
3. Stack-ready stories at least double: dev-train **≥22**, dev-holdout **≥10**.
4. At least **three construction-specific blocker classes** are fully served.
5. Collision, quarantine, ambiguous-reading, and clause-split counts do not
   exceed the baselines above; no wrong-hazard or `DECL→WRONG` may appear.

### Phase B build order

1. **Conjunctive disjuncts / `entity-in-raw-or`** — strongest cross-split
   marginal gain, existing disjunction facts and synths, narrow reader cost.
2. **Decompose `entity-raw-other` by actual construction**, then build only
   its cheapest cross-split family. Initial samples include generics,
   existential composition, resultative/participial predicates, enumeration,
   and relation chains; the catch-all itself is not an implementation class.
3. **Price one narrow passive or relative-clause family** using exact emitted
   key shapes and composition buyers; passive currently has the stronger
   balanced marginal estimate.
4. Re-survey `entity-in-raw-if`, compound generics, and all banked zeros after
   each landed class. Do-support negation, unresolved scope, and paraphrase
   stay banked until their join surface acquires a measured two-split buyer.

## Phase B reader 1 — ground both-or-neither equivalence (2026-07-20)

The first `entity-in-raw-or` construction is served: **“NAME is either
[both] A and B, or [PRONOUN is] neither”**. This is not an ordinary binary
disjunction and is not represented by stuffing a conjunction into one opaque
predicate key. Its exact classical content is the ground equivalence
`A(NAME) ↔ B(NAME)`.

The shared model therefore gains `Equivalence(entity, left, right)`, but the
fact is reachable only from two anchored scratch-pack readers. It asserts no
Atom by itself. Two pack synths transfer an already established polarity in
either direction; explicit falsity propagates exactly like truth. They carry
no `unless`, deliberately: a propagated opposite must collide so the normal
quarantine path and reductio's throwaway store can observe the contradiction.
The readers require the final period and refuse negation or additional
coordination inside a predicate, so a larger trailing construction cannot be
partially consumed.

Synthetic contract: exact fact shape, no unsupported atoms, positive and
negative propagation, universal-chain composition, reductio composition, a
negated-conjunct minimal pair, and a larger-construction refusal. **pytest
1959 passed; scratch lint 0 errors; curated 65/65.** Every benchmark slice is
NEUTRAL against the last behavior baseline: difg dev, GSM8K dev-train and
dev-holdout, ASDiv, SVAMP, MAWPS, SciBench, and the safety-only FOLIO dev gate
all report **0 BROKE / 0 DECL→WRONG**.

### Bought reader movement

| grouped split | fact-bearing | fully read | stack-ready items / stories | target raw-or premises | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1327→1329 | 720→722 (+2) | 14/11→16/12 | 17→15 | 666→664 |
| dev-holdout | 1295→1295 | 721→726 (+5) | 6/5→7/6 | 38→35 | 614→609 |

Hazards are unchanged on both splits: collision 8/12, quarantine 16/24,
ambiguous readings 51/33, clause split 0/0 (train/holdout). No verdict moves:
verdict-gold stays 20 correct / 305 declined on train and 1 / 291 on holdout.
The complete folio-with-logic gate likewise stays 20 correct / 1 persistent
poisoned-text wrong / 473 declined on train and 1 / 0 / 424 on holdout.

The increment is bought under the Phase B rule because both fully-read and
stack-ready-story coverage move on **both** grouped splits. The rest of
`entity-in-raw-or` remains heterogeneous: verbal alternatives, conditional
alternatives, repeated `neither A nor B`, and larger signed conjunctions are
separate construction families. Re-survey them independently; do not widen
this reader or call the whole catch-all served.

## Phase B reader 2 — unrestricted bare-plural disjunction (2026-07-20)

The Stage 8 banked family now has a cross-split buyer: **“CLSs are [either]
L or R.”** Two pack-only readers reuse `QuantifiedDisjunction` and the existing
instantiation, case-analysis, DS, and XOR synths. Bare `or` is inclusive and
overt `either` is exclusive, exactly matching Stage 3's measured contract.
The existing `bare_plural` slot carries the whole safety boundary: counted,
definite, possessive, and qualified subjects refuse. Negated or larger
coordinated disjuncts remain unread.

Synthetic contract: inclusive instantiation + case analysis, exclusive
elimination, four non-generic subject refusals, and a larger-disjunct refusal.
**pytest 1966 passed; scratch lint 0 errors.** The full benchmark matrix is
NEUTRAL against reader 1: curated 65/65, plus difg dev, GSM8K dev-train and
dev-holdout, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO dev all at **0 BROKE /
0 DECL→WRONG**. Folio-with-logic verdicts remain 20 correct / 1 persistent
poisoned-text wrong / 473 declined on train and 1 / 0 / 424 on holdout.

### Incremental reader movement

| grouped split | fact-bearing | fully read | stack-ready items / stories | target raw-or premises | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1329→1329 | 722→724 (+2) | 16/12→16/12 | 15→15 | 664→662 |
| dev-holdout | 1295→1295 | 726→727 (+1) | 7/6→8/7 | 35→34 | 609→608 |

Every hazard stays at the Phase A baseline. The train reader removes a real
truth-scope blocker even though the query-overlap heuristic did not label that
story `entity-in-raw-or`; the holdout reader also creates one stack-ready
story. This is the second fully served construction class toward Phase C's
three-class minimum.

The mandatory banked-zero recheck remains **zero** for all three joins. The
new generic keys use regular `-s` singularization (`bananas`) or a registered
noun (`events`), so the `_naive_singular` `-se/-ce/-ze` fix cannot participate.
Neither story introduces a CamelCase entity. Their conclusions are copular,
not verbal-universal asks. Keep all three banked.

## Phase B reader 3 — negative two-article indefinite generic (2026-07-21)

The cheapest genuine cross-split family inside the `entity-raw-other` survey
is now served: **“A/An CLS is not a/an PRED.”** The new pack-only reader is the
negative sibling of Stage 9i's positive indefinite generic and emits the
existing `Quantified(cls, pred, polarity=false)` shape. It admits no vocabulary
globally: the two articles, copula, and explicit negator anchor unknown corpus
nouns such as `god`, `destroyer`, and `podcast`. Articleless adjectival
predicates and coordinated predicates remain unread as separate constructions.

The existing universal-instantiation synth buys composition directly:
`A trout is not a flyer` plus `Rex is a trout` derives `not flyer(Rex)`.
Synthetic falsification pins the exact fact, absence of a ground atom, the
positive minimal pair, the articleless refusal, and refusal of a larger
coordinated predicate. The pre-existing Stage 9i test that explicitly banked
the negative form was intentionally updated to the new fact contract.
**pytest 1971 passed; scratch lint 0 errors; curated 65/65.** All eight standard
snapshot comparisons are NEUTRAL: difg dev, GSM8K dev-train/dev-holdout,
ASDiv, SVAMP, MAWPS, SciBench, and the safety-only FOLIO dev gate each report
**0 BROKE / 0 DECL→WRONG**.

### Incremental reader movement

| grouped split | fact-bearing | fully read | stack-ready items / stories | target raw-other items / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1329→1331 | 724→726 (+2) | 16/12→16/12 | 9/9→9/9 | 662→662 |
| dev-holdout | 1295→1297 | 727→729 (+2) | 8/7→8/7 | 15/11→14/10 | 608→608 |

The emitted rule occurs in two verdict-gold train item instances across one
story (`A god is not a destroyer`) and three holdout instances across two
stories (`A phone is not a computer`; `A podcast is not a novel`). Two holdout
instances newly become fully read; the third premise was already fact-bearing
through other machinery. No verdict converts. Hazards remain exactly at the
Phase A baselines: collision 8/12, quarantine 16/24, ambiguous readings 51/33,
and clause split 0/0 (train/holdout). Folio-with-logic also remains 20 correct /
1 persistent poisoned-text wrong / 473 declined on train and 1 / 0 / 424 on
holdout, with both diffs NEUTRAL.

This is the third served construction class, but it does not trigger Phase C:
cumulative fully-read coverage is only 726/1647 and 729/1602, truth-scope
vetoes are 662 and 608, and stack-ready stories are 12 and 7, all below the
pre-registered thresholds.

The mandatory banked-zero recheck is again **zero**. Reader 3's keys contain
none of the `_naive_singular` `-se/-ce/-ze` endings, no CamelCase entity, and
no verbal-universal conclusion. Keep all three infrastructure ideas banked.

### Survey banks before reader 4

- **Existential “there is/exists” is not one construction.** The train surface
  says “There exist both harmful and beneficial controlled substances” and
  needs a conjoined-property existential plus witness/class propagation. The
  two simple holdout surfaces need PP/resultative phrase composition to join
  their conclusions. A bare `there is` reader alone is unbought.
- **Direct `… was/is VERBed by NAME` passives are vocabulary-blocked at the
  shared join.** The clean train participle (`produced`) has a multi-token
  unknown subject, while holdout's `edited`/`announced` participles and name
  tails are not currently canonical verb/name units. Span-only extraction
  would mint non-joining verb keys. Bank until a measured lemma/name increment
  has buyers on both splits.
- The next increment should re-price a narrow passive or relative-clause
  family, then compound generics and `entity-in-raw-if`. Do not widen reader 3
  into articleless predicates or complex negative subjects.

## Phase B reader 4 — single-antecedent verbal “Everyone who” (2026-07-21)

The narrow relative-clause family **“Everyone who V P V2 Q”** is now served as
the universal implication `V(P) → V2(Q)`. `Quantified.cls` is intentionally an
arbitrary predicate key, not only a noun class, so named ground-verbal atoms
join the existing universal-instantiation synth directly. The landed DEV keys
are `work for government department → pay tax on their salary` and
`rent car → spend money`; no new fact type, synth, consumer, or vocabulary is
introduced.

The first pack-only draft also matched “Everyone who gets up early catches the
sunrise,” but condensation represents `gets up` as one verb unit carrying the
base lemma `get`. Emitting `get early` would conflate the particle predicate
with an unrelated “get early.” The shared matcher therefore gains an opt-in,
default-false `single_word` slot constraint that requires one original token.
Reader 4 enables it on both verbs, refusing particle and perfect merges. This
is structural rather than lexical and leaves every pre-existing rule
byte-identical. The lossy story remains unread.

Synthetic contract: exact `Quantified` key shape, a `Someone` minimal pair,
named-witness composition, negated-consequent refusal, coordinated-antecedent
refusal, modal-consequent refusal, and the particle-key-loss refusal. **pytest
1978 passed; scratch lint 0 errors; curated 65/65.** Because the opt-in field
lives in the shared kernel,
the complete matrix was treated as live blast radius. All eight standard
snapshot comparisons and both folio-with-logic comparisons are NEUTRAL at
**0 BROKE / 0 DECL→WRONG**.

### Incremental reader movement

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1331→1331 | 726→728 (+2) | 16/12→16/12 | 2 / 1 | 662→662 |
| dev-holdout | 1297→1297 | 729→730 (+1) | 8/7→8/7 | 1 / 1 | 608→608 |

No verdict converts. Hazards remain at the Phase A baselines: collision 8/12,
quarantine 16/24, ambiguous readings 51/33, and clause split 0/0
(train/holdout). Folio-with-logic remains 20 correct / 1 persistent
poisoned-text wrong / 473 declined on train and 1 / 0 / 424 on holdout.

Cumulative campaign state is now 728/1647 and 730/1602 fully-read premises,
662 and 608 truth-scope vetoes, and 12 and 7 stack-ready stories. Four
construction classes are served, but the Phase C thresholds remain 852/850
fully read, 499/460 truth-scope vetoes, and 22/10 stack-ready stories.

The mandatory banked-zero recheck remains **zero**: no verdict moved, the
landed keys contain no `_naive_singular` ending or CamelCase entity, and no
represented verbal-universal conclusion joins them. Keep those banks closed.

**Next:** re-survey compound generics and `entity-in-raw-if` for reader 5. The
direct passive-agent and existential families remain banked under reader 3's
recorded composition/vocabulary blockers; do not reopen them without a new
cross-split buyer.

## Phase B reader 5 — verbal-restrictor conditional (2026-07-21)

The `entity-in-raw-if` family **“If a CLS V P, then it is Q”** is now served by
the existing `Conditional(cls, pred, then_pred, polarity=true)` contract. The
class membership and verbal antecedent must both hold before the existing
conditional-instantiation synth derives the copular consequence. Antecedent
keys render through the same `{v} {p}` path as `ground-verbal`; reader 4's
opt-in `single_word` gate refuses particle/perfect merges that would lose part
of the predicate.

The landed train key is `competitive sport + involves spectators betting on
small game → banned`; the holdout key is `technique + provides spatial
resolution of brains → measurement of brain activity`. No vocabulary, fact
type, synth, consumer, or kernel code changes. Negated consequences,
coordinated or modal antecedents, copular antecedents, and particle verbs remain
separate constructions.

Synthetic contract: exact `Conditional` shape, copular-antecedent minimal
pair, full class+verbal named-witness composition, and refusals for negative
consequences, coordination, modality, and particle-key loss. **pytest 1985
passed; scratch lint 0 errors; curated 65/65.** All eight standard snapshots
and both folio-with-logic comparisons are NEUTRAL at **0 BROKE / 0
DECL→WRONG**.

### Incremental reader movement

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1331→1333 (+2) | 728→730 (+2) | 16/12→16/12 | 2 / 1 | 662→660 (-2) |
| dev-holdout | 1297→1300 (+3) | 730→733 (+3) | 8/7→8/7 | 3 / 1 | 608→605 (-3) |

No verdict converts. Hazards remain at the Phase A baselines: collision 8/12,
quarantine 16/24, ambiguous readings 51/33, and clause split 0/0
(train/holdout). Folio-with-logic remains 20 correct / 1 persistent
poisoned-text wrong / 473 declined on train and 1 / 0 / 424 on holdout.

Cumulative campaign state is 730/1647 and 733/1602 fully-read premises, 660
and 605 truth-scope vetoes, and 12 and 7 stack-ready stories. Five construction
classes are served, but the Phase C thresholds remain 852/850 fully read,
499/460 truth-scope vetoes, and 22/10 stack-ready stories.

The mandatory banked-zero recheck remains **zero**: no verdict moved, the new
keys contain no `_naive_singular` ending or CamelCase entity, and no represented
verbal-universal conclusion joins them. Do-support negation also remains at
zero estimated stack gain on both splits (63/29 train items/stories; 41/20
holdout). Compound generics remain asymmetric at zero train versus one holdout
estimated stack-ready story.

**Next:** price the remaining cross-split negative-antecedent ground conditional
family for reader 6: train's repeated-name `If Marvin is not from Earth, then
Marvin is an extraterrestrial` and holdout's anaphoric `If Leon is not pursuing
a bachelor's degree, then he is a professor`. This needs a dedicated ground
implication fact and synth; do not encode a name as `Conditional.cls` or mix in
cross-entity/modal conditionals.

## Phase B reader 6 — negative-antecedent same-entity ground conditional (2026-07-21)

The safe subset of the family above is served by a dedicated fact: **“If NAME
is not P, then NAME is Q”** →
`GroundConditional(entity, pred, then_pred, then_polarity)`,
semantics ¬P(e) → Q(e). The negation is STRUCTURAL (the reading consumes
`not` as skeleton, so `pred` holds plain P), and a name never rides
`Conditional.cls`. The repeated-name surface is pinned by `same_lemma` (the
9i precedent). The initially landed literal-`he` surface was removed after
review: it consumed the pronoun as skeleton without checking its unresolved
`refers` obligation, so “If Alice is not taller than Bob, then he is happy”
could confidently assert that Alice was happy. Pronoun consequents stay
unread until coreference is represented as evidence. Both spans refuse
negation, coordination, and either/neither
marking, so the coordinated surfaces (Mike/Emily/Clyde/Thomas/Carol) stay
whole-unread. Cross-entity consequents fail `same_lemma`. The
positive `he`, negative-consequent `they` (`If Nancy is not a teacher, then
they are not paid by the school` — one train story, no holdout twin), and the
`she` twin are BANKED pending sound coreference evidence. Neither `pred` nor
`then_pred` decomposes (non-monotone antecedent position; a false-polarity
consequent would widen under stripping).

One synth, `synth/ground-conditional-fire`: gc + explicit `Atom(e, P,
polarity=false)` ⊢ `Atom(e, Q, then_polarity)`, deliberately `unless`-free
(the equivalence/disj-conditional precedent) so an opposite consequent
COLLIDES. That choice makes the contrapositive FREE: the 9i reductio engine
assumes ¬P, this synth emits Q, the collision with a stated ¬Q refutes the
hypothesis, and P commits — pinned as
`test_contrapositive_comes_free_via_reductio`; no tollens synth exists or is
needed.

Synthetic contract (11 pins): exact repeated-name fact shape, simple and
ambiguous-pronoun refusal, cross-entity refusal, positive-antecedent refusal,
coordinated-antecedent refusal, banked negative-consequent refusal,
explicit-antecedent fire, open-world undecided antecedent, reductio
contrapositive, and contradictory-consequent quarantine. **The targeted 11
tests pass; scratch lint has 0
errors; curated 65/65.** The fact kind touches the shared kernel
(model/patterns/schemas registration), so the complete matrix ran as live
blast radius: all eight standard snapshot diffs NEUTRAL (difg dev, GSM8K
dev-train/dev-holdout, ASDiv, SVAMP, MAWPS, SciBench, FOLIO dev — 0 BROKE,
0 DECL→WRONG), and both folio-with-logic comparisons item-level neutral in
OUTCOME AND REASON (train 20 correct / 1 persistent poisoned-text wrong /
473 declined; holdout 1 / 0 / 424).

### Incremental reader movement

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1333→1333 | 730→732 (+2) | 16/12→16/12 | 2 / 1 | 660→658 (-2) |
| dev-holdout | 1300→1300 | 733→733 | 8/7→8/7 | 0 / 0 | 605→605 |

The item-level movers are the two Marvin items and nothing else. The Leon
surface and its permissive-fold `Membership('leon','degree')` leak remain
unread; resolving that diagnostic issue does not justify assuming pronoun
coreference. No hazard count moves on either split; no verdict converts
(Marvin's stack still needs the compound-cls universal).

Six construction classes are served. Cumulative campaign state: 732/1647
and 733/1602 fully-read premises, 658 and 605 truth-scope vetoes, and 12
and 7 stack-ready stories — all still below the Phase C thresholds
(852/850, ≤499/460, ≥22/10).

⚠ **Classifier regeneration note (this session):** the throwaway Phase A
classifier was rebuilt from the recorded definitions. It reproduces the
premise universe (1647/1602 over the actionable decline pool), fact-bearing,
truth-scope vetoes, hazards (quarantine counts QUARANTINED FACTS, collision
counts items), and every reader's incremental movement EXACTLY, but its
fully-read total sits a CONSTANT −4 (train) / −11 (holdout) below the
recorded scale at both endpoints, and its stack-ready count −4/−2 items —
some Phase A blocker nuance was not recovered. Movement (deltas) is
frame-independent and is what the table above reports; cumulative numbers
are stated in the RECORDED frame by adding deltas to the reader-5 totals.

The mandatory banked-zero recheck remains **zero**: the new keys carry no
`_naive_singular` `-se/-ce/-ze` ending, no CamelCase entity, and no
represented verbal-universal conclusion joins them. Do-support negation and
compound generics keep their recorded estimates (no join-surface change for
`have`/`do` keys).

**Next:** the priced `entity-raw-other` and passive families are still
banked on composition/lexical infrastructure (reader 3's record). Re-price a
narrow passive or relative-clause family per the Phase A build order, and
re-survey compound generics and `entity-in-raw-if` for a new cross-split
buyer now that six classes are served.

## Phase B reader 7 — plural-generic `people` conditionals (2026-07-21)

The post-reader-6 re-survey found a cheaper cross-split conditional class:
**“If people are P, then they are [not] Q”**. Bare `people` is the
plural-agreeing form of the unrestricted human quantifier already represented
by the `someone` reader, so this increment reuses
`Quantified(cls, pred, polarity)` and `synth/universal-instantiation`. Both
keys render through `.singular`, matching the established Stage 8d/9a rule
that a plural-agreeing predicate must meet singular ground-atom keys. No new
kernel machinery or fact kind is introduced.

The construction is exact and copular: `if` / `people` / `are` / P / `then` /
`they` / `are` / [explicit `not`] / Q. The consequent pronoun carries the
generic subject variable; unlike reader 6's removed literal-`he` rule, it is
never grounded to a named entity. Verbal and do-support consequences,
negated antecedents, and the singular `someone` sibling stay whole-unread.
Multiword predicates remain exact phrase keys; treating an internal modifier
or participial phrase as opaque can only narrow a join, never erase words and
loosen one.

The nine-test synthetic contract pins positive and negative exact facts, the
passive-participial key shape, universal-instantiation composition and its
unmet-antecedent null, plus four larger/minimal-pair refusals. **pytest 2,005
passed; scratch lint 0 errors; curated 65/65.** All eight standard DEV
snapshot diffs are NEUTRAL: difg dev, GSM8K dev-train/dev-holdout, ASDiv,
SVAMP, MAWPS, SciBench, and FOLIO each report 0 BROKE and 0 DECL→WRONG.
The standard projects do not load the scratch pack, but the explicit matrix
pins that blast-radius assumption.

The in-memory DEV-only before/after comparison removed only the two reader-7
rule IDs from the baseline registry, leaving the reader-6 pronoun correction
present on both sides. Folio-with-logic is item-level neutral in OUTCOME AND
REASON on both splits (train 20 correct / 1 persistent poisoned-text wrong /
473 declined; holdout 1 / 0 / 424):

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1333→1333 | 732→734 (+2) | 16/12→16/12 | 2 / 1 | 658→656 (−2) |
| dev-holdout | 1300→1300 | 733→739 (+6) | 8/7→8/7 | 6 / 3 | 605→599 (−6) |

The train movement is one negative-consequent generic story. Holdout moves
three stories: two positive-consequent predicates and one negative. No item
becomes all-premises-read, so stack readiness remains 12/7 stories and no
conversion null is required. Collision and quarantine stay 8/12 and 16/24;
ambiguous-reading and clause-split hazards do not increase. Diagnostic
agreement events improve 86→84 on holdout. The only new semantics are four
intended `Quantified` keys and one existing intersective narrowing; no new
ground atom instantiates and no answer reason changes.

Seven construction classes are served. Cumulative recorded-frame state is
734/1647 and 739/1602 fully-read premises, 656 and 599 truth-scope vetoes,
and 12 and 7 stack-ready stories. All numeric Phase C thresholds still bind
(852/850, ≤499/460, ≥22/10).

The mandatory banked-zero recheck remains zero: the new keys carry no
`_naive_singular` ending, CamelCase entity, or represented verbal-universal
ask, and no existing bank joins to a verdict or a newly all-read stack.
Adjacent verbal and do-support `people` conditionals show one-sided potential
but remain distinct construction families; re-price them across both grouped
splits before implementation. The narrow passive/relative family remains the
next broad build-order lever. No TEST look was spent.

## Phase B reader 8 — class-scoped bare-plural copular relatives (2026-07-21)

The next narrow relative family is **“CLSs who are P are [not] Q”**. Its
semantics require two antecedents, `CLS(e)` and `P(e)`, so it maps directly to
the existing `Conditional(cls, pred, then_pred, polarity)` fact and
`synth/conditional-instantiation`. It must not reuse reader 7's unrestricted
`Quantified(P,Q)` representation: “pets who are naughty” does not license the
consequence for every naughty entity. The class, relative property, and
consequence all occur in plural-agreeing positions and therefore render with
the established `.singular` key discipline.

Two polarity rules own the entire copular construction. An explicit final
`not` alone sets negative consequence polarity. Negative or verbal relatives,
verbal consequences, definite/count-qualified plural subjects, and singular
subjects fail the exact match and remain whole-unread. The ten-test synthetic
contract pins both exact fact shapes, successful composition, missing-class
and missing-property nulls, and every refusal boundary.

**pytest 2,015 passed; scratch lint 0 errors; curated 65/65.** All eight
standard DEV snapshot diffs are NEUTRAL: difg dev, GSM8K
dev-train/dev-holdout, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO each report 0
BROKE and 0 DECL→WRONG. Folio-with-logic also remains outcome-neutral (train
20 correct / 1 persistent poisoned-text wrong / 473 declined; holdout 1 / 0 /
424):

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1333→1333 | 734→736 (+2) | 16/12→16/12 | 2 / 1 | 656→654 (−2) |
| dev-holdout | 1300→1300 | 739→742 (+3) | 8/7→8/7 | 3 / 1 | 599→599 |

The train buyer is a positive `people` relative; the holdout buyer is a
negative `pets` relative. Neither story becomes all-premises-read, so stack
readiness and verdict outcomes remain unchanged. The holdout whole read does
remove a harmful permissive-fold byproduct: three repeated item collisions
disappear (**12→9**) and six quarantined facts disappear (**24→18**). Their
reasons move from contradictory `pet/be` fold facts to honest
missing-logic/no-ask declines. Agreement ambiguity, ambiguous-reading, and
clause-split diagnostics do not increase.

Eight construction classes are served. Cumulative recorded-frame state is
736/1647 and 742/1602 fully-read premises, 654 and 599 truth-scope vetoes,
12 and 7 stack-ready stories, collision 8/9, and quarantine 16/18. All numeric
Phase C thresholds still bind (852/850, ≤499/460, ≥22/10).

The mandatory banked-zero recheck remains zero: the emitted keys carry no
`_naive_singular` ending, CamelCase entity, or represented verbal-universal
ask, and no item becomes a new all-read stack. Re-price the adjacent
verbal/do-support `people` conditionals and the remaining passive/relative
families against this cleaner state before reader 9. No TEST look was spent.

## Phase B reader 9 — restricted Everyone disjunctions (2026-07-21)

The next bought raw-coordination family is **“Everyone RESTRICTION is
[either] L or R”**. `Everyone` contributes the universal variable; the
non-empty restriction contributes the joinable antecedent predicate. The two
rules reuse `QuantifiedDisjunction` and `synth/qdisj-instantiation`; subsequent
case analysis is already shared. Bare `or` remains inclusive and explicit
`either` exclusive. Empty restrictions, relatives, negated or verbal
disjuncts, and three-way forms remain whole-unread.

Eleven synthetic tests pin both exact fact shapes, successful composition,
the missing-restriction and branch-non-decomposition nulls, and all refusal
boundaries. **pytest 2,026 passed; scratch lint 0 errors with the same eight
warnings; curated 65/65.** All eight standard DEV snapshot diffs and both
FOLIO-with-logic grouped diffs are NEUTRAL: 0 BROKE and 0 DECL→WRONG.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1333→1335 (+2) | 736→738 (+2) | 16/12→17/13 (+1/+1) | 2 / 1 | 654→652 (−2) |
| dev-holdout | 1300→1300 | 742→745 (+3) | 8/7→8/7 | 3 / 2 | 599→596 (−3) |

The train story crosses the stronger all-premises-read and stack-ready
boundary for its represented conclusion; the sibling negative conclusion
still has no ask shape. Holdout's three premises were already fact-bearing
through coarse readings, but the exact reader consumes their truth-scoping
`or`, so fully-read coverage moves without inventing a second fact path.
Outcomes, reasons, collision, quarantine, agreement, ambiguous-reading, and
clause-split diagnostics remain unchanged.

The pre-reader survey banked three candidates rather than widening them:
positive verbal `people` consequences do not share a train/holdout ground-key
contract; outer-quantified verbal relatives emitted facts for 9/8 instances
but moved no registered metric; and verbal both-or-neither would require the
same unsupported coreference assumption removed from reader 6. The normal
banked-zero recheck (`_naive_singular`, CamelCase entities,
verbal-universal asks) remains zero. Cumulative recorded-frame state is
738/1647 and 745/1602 fully read, 652/596 truth-scope vetoes, 13/7
stack-ready stories, collision 8/9, and quarantine 16/18. Every numeric Phase
C threshold still binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** re-price the remaining exact raw-coordination and conditional
families against reader 9's newly stack-ready train story. Do-support,
unresolved coreference, direct passive-agent infrastructure, and paraphrase
bridges remain banked until a two-split buyer appears.

## Phase B reader 10 — two-article indefinite-generic disjunctions (2026-07-21)

The next bought raw-coordination family is **“A/An CLS is either a/an L or
a/an R”**. It is singular-agreeing and therefore renders all three keys plain,
exactly like `universal-indefinite-copular`. The leading article licenses a
generic class; explicit `either` licenses exclusivity. The existing
`QuantifiedDisjunction`, `synth/qdisj-instantiation`, and case-analysis/XOR
synths supply the entire semantic path.

The first prototype accepted articleless branches and measured +5/+7
fully-read instances, but failed its larger-construction falsification:
`span_blocks: verb` cannot detect a quarantined unknown verb, so an unknown
verbal branch followed by an adverb could ride an opaque predicate span. The
shipped reader requires `a/an` on both branches, structural evidence that
they are nominal. This deliberately banks the articleless adjective and
unknown-word surfaces despite their additional measured coverage.

Fourteen synthetic tests pin exact exclusive fact shape, case-analysis and
XOR composition, the missing-class null, plus missing-article, bare-`or`,
quantifier/definite-subject, coordinated-class, negated, prepositional,
verbal, and three-way refusals. **pytest 2,040 passed; scratch lint 0 errors
with the same eight warnings; curated 65/65.** All eight standard DEV
snapshot diffs and both FOLIO-with-logic grouped diffs are NEUTRAL: 0 BROKE
and 0 DECL→WRONG.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1335→1337 (+2) | 738→740 (+2) | 17/13→17/13 | 2 / 1 | 652→650 (−2) |
| dev-holdout | 1300→1303 (+3) | 745→748 (+3) | 8/7→8/7 | 3 / 1 | 596→593 (−3) |

The repeated train function premise and holdout neuroimaging premise are the
only buyers. Each gains one exact `QuantifiedDisjunction`; neither has a
matching named class witness, so no ground disjunction instantiates and no
item becomes all-premises-read or stack-ready. Outcomes and reasons remain
unchanged (train 19 correct / 1 pre-existing wrong / 474 declined; holdout
1 / 0 / 424), as do collision, quarantine, agreement, ambiguous-reading, and
clause-split diagnostics.

The mandatory banked-zero recheck remains zero: no `.singular` unknown-word
fold runs, `QuantifiedDisjunction` has no entity field, and the new keys do not
join a verbal-universal ask. Cumulative recorded-frame state is 740/1647 and
748/1602 fully read, 650/593 truth-scope vetoes, 13/7 stack-ready stories,
collision 8/9, and quarantine 16/18. Every numeric Phase C threshold still
binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** re-price a structurally gated articleless disjunction class and the
remaining exact conditional families. Stative/modal/do-support negative
universals, direct passive-agent infrastructure, and unresolved coreference
remain banked until a single two-split key contract appears.

## Phase B reader 11 — negative possessive universals (2026-07-21)

The next bought universal family is **“No CLSs have P” / “No CLS has P”**.
The agreement pair emits one shared negative `Quantified` predicate key,
`have P`; the plural frame folds only the class key and the singular frame
keeps it plain. Existing universal instantiation and universal chaining carry
the semantics without a new fact or synth.

The simple frame excludes the adjacent lookalikes structurally. The class
span blocks verbs and capacity/future modals, so relative restrictions and
`can/will have` forms cannot become an opaque class. The predicate blocks a
second verb, negation, and coordination, refusing perfect, double-negative,
and coordinated predicates. Twelve synthetic tests pin both fact shapes,
subclass chaining, named instantiation, and eight refusal boundaries.

**pytest 2,052 passed; scratch lint 0 errors with the same eight warnings;
curated 65/65.** All eight standard DEV snapshot diffs and both
FOLIO-with-logic grouped diffs are NEUTRAL: 0 BROKE and 0 DECL→WRONG.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1337→1338 (+1) | 740→741 (+1) | 17/13→17/13 | 1 / 1 | 650→649 (−1) |
| dev-holdout | 1303→1304 (+1) | 748→751 (+3) | 8/7→8/7 | 3 / 2 | 593→590 (−3) |

The train buyer is the single `No humans have hooves` premise. Holdout buys
two stories: `No women have prostate cancer` and `No reptile has fur`. The
reptile denial chains through the existing `snake → reptile` fact to derive
`snake → not have fur`, and its item becomes all-premises-read. The question
`Some snake has fur` still has no ask shape, however, so the item remains an
honest decline and stack readiness does not move. Outcomes and reasons remain
unchanged (train 19 correct / 1 pre-existing wrong / 474 declined; holdout
1 / 0 / 424), as do collision, quarantine, agreement, ambiguous-reading, and
clause-split diagnostics.

The banked-zero recheck remains zero: the plural key uses registered ordinary
morphology, `Quantified` carries no entity field, and the possessive
universal has no represented ask join. Cumulative recorded-frame state is
741/1647 and 751/1602 fully read, 649/590 truth-scope vetoes, 13/7
stack-ready stories, collision 8/9, and quarantine 16/18. Every numeric Phase
C threshold still binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** continue the Phase B premise-reader survey with exact conditional
and passive/relative families. The now-all-read snake story exposes a
possessive existential ask gap, but that is not a premise-reader class and
stays banked unless the campaign scope explicitly expands. Articleless
unknown-word disjunctions, do-support, unresolved coreference, and direct
passive-agent infrastructure remain banked.

## Phase B reader 12 — plural negative event universals (2026-07-21)

The next bought universal family is **“No CLSs V P”**, where `V` is a
bare-form, single-token non-state verb. The plural agreement licenses
`.singular` on the class key, while the full `V P` predicate remains unfolded
and exact. The reader emits the existing negative `Quantified` fact, so the
existing universal-chain and universal-instantiation synths supply all
composition without a new fact kind or kernel path.

The initial broad draft measured +4/+6 fully-read instances, but one holdout
story was a false relative-clause parse: `who` rode inside the class span, its
relative verb filled `V`, and an unknown real main verb was swallowed into
`P`. The landed rule blocks the structural senses used by `who`, `that`, and
`which` (`interrogative`, `complementizer`, `wh_which`) in addition to verbs,
modals, negation, and coordination. The predicate also refuses a second verb,
modals, negation, coordination, and counted material. This narrows the DEV
buyers to exactly the intended two story families.

Fifteen synthetic tests pin the exact negative fact, subclass chaining,
named instantiation, and twelve minimal/larger refusal boundaries: positive
quantification, singular agreement, modal, three relative markers,
do-negation, coordinated class, coordinated predicate, perfect, particle
verb, and counted predicate. **pytest 2,067 passed; scratch lint 0 errors with
the same eight warnings; curated 65/65.** All eight standard DEV snapshot
diffs and both FOLIO-with-logic grouped diffs are NEUTRAL: 0 BROKE and 0
DECL→WRONG.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 741→745 (+4) | 17/13→17/13 | 4 / 1 | 649→645 (−4) |
| dev-holdout | 1304→1304 | 751→754 (+3) | 8/7→8/7 | 3 / 1 | 590→587 (−3) |

Train buys the repeated negative student/destination premise; holdout buys
the repeated Russian-Federation-official/citizenship premise. The only new
semantics are their exact negative `Quantified` keys. No named class witness
in either represented stack instantiates a verdict-relevant atom, so
all-premises-read, stack readiness, outcomes, and reasons remain unchanged
(train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined;
holdout 1 / 0 / 424). Collision, quarantine, agreement, ambiguous-reading,
and clause-split hazards also remain unchanged.

The banked-zero recheck remains zero: the one unknown plural uses ordinary
`-s` folding rather than the banked `-se`/`-ce`/`-ze` cases, no entity field
is introduced, and neither story presents a represented verbal-universal ask
join. Cumulative recorded-frame state is 745/1647 and 754/1602 fully read,
645/587 truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and
quarantine 16/18. Every numeric Phase C threshold still binds (852/850,
≤499/460, ≥22/10). No TEST look was spent.

**Next:** re-price the remaining exact conditional and passive/relative
families against reader 12. Do-support negation, unresolved coreference,
articleless unknown-word disjunctions, and direct passive-agent infrastructure
remain banked until an exact cross-split key contract appears.

## Phase B reader 13 — named do-support event denials (2026-07-21)

The post-reader-12 single-veto survey found a narrow bought slice inside the
previously demoted do-support bucket: **“NAME does not V P”** with a
bare-form, single-token non-state event verb. The explicit `not` supplies
negative polarity; `V P` renders through the same path as ground-verbal, so
the result is an exact negative `Atom` consumable by the existing logic
verdict path. A synthetic positive verbal question is refuted directly,
proving this is a current join rather than an inert fact shape.

The construction keeps the Stage 6 be-twin boundary intact. `nonstate_verb`
refuses copulas and stative possession; `bare_form` and `single_word` refuse
inflected/condensed verbs; the predicate blocks another verb, modal,
negation, coordination, disjunction, and counted material. The nearby
holdout `own` denial therefore remains a separate stative class with no
represented flat-event consumer, not an excuse to weaken the gate.

Thirteen synthetic tests pin the exact negative fact, refutation of the
matching positive question, a different-entity null, and positive,
do-emphatic, stative `own`/`have`, plural/coordinated subject, coordinated
predicate, multi-verb, particle, counted, and embedded-conditional refusals.
**pytest 2,080 passed; scratch lint 0 errors with the same eight warnings;
curated 65/65.** All eight standard DEV snapshot diffs and both
FOLIO-with-logic grouped diffs are NEUTRAL: 0 BROKE and 0 DECL→WRONG.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 745→749 (+4) | 17/13→17/13 | 4 / 2 | 645→641 (−4) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

The two train buyers are repeated named denials for working at a pool and
catching the sunrise. Their new facts are exact and consumer-compatible, but
other gaps in those stories keep all-premises-read, stack readiness, and
outcomes unchanged (train 19 correct / 1 pre-existing poisoned-text wrong /
474 declined; holdout 1 / 0 / 424). Collision, quarantine, agreement,
ambiguous-reading, and clause-split hazards also remain unchanged.

Before selecting this class, a subject-relative verbal `All CLSs who/that V
P V2 Q` prototype was re-measured. It emitted one semantically valid holdout
`Conditional` across five item instances, but changed no fact-bearing,
fully-read, veto, stack, hazard, outcome, or reason metric and matched no
train item. It was removed under the enabler-must-be-bought rule. Direct
passive examples remain structurally asymmetric across splits and mostly
occur inside cross-entity conditionals or disjunctions; object relatives need
binary relation direction rather than a unary phrase key.

The banked-zero recheck remains zero: no singular fold or CamelCase entity is
involved, and no represented verbal-universal ask joins the new keys.
Cumulative recorded-frame state is 749/1647 and 754/1602 fully read, 641/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Every numeric Phase C threshold still binds (852/850, ≤499/460,
≥22/10). No TEST look was spent.

**Next:** re-price remaining exact coordination and conditional families.
Passive/cross-entity relations, object relatives, stative ownership, the
zero-movement outer-relative reader, articleless unknown-word disjunctions,
and unresolved pronoun conditionals remain banked until their missing
structure or consumer join is bought.

## Phase B infrastructure — event-reader exclusion is not arithmetic state (2026-07-21)

Reader 14's future-event-disjunction falsification found that bare `be` was
verb-sensed but absent from `state`, so `nonstate_verb` admitted a copular
branch. Simply adding `be`/`been`/`being` to `state` was unsafe: that category
selects arithmetic holding facts, and the full gate caught a GSM8K temporal
age item moving from decline to a confident wrong (expected 16, got 6).

The bought prerequisite separates those meanings structurally.
`non_event_verb` is now the parent of `state`; every existing state member
therefore remains excluded from event readers, while difg-mined's three bare
or participial copular forms join only `non_event_verb`. The legacy DSL type
name `nonstate_verb` remains stable but checks the broader boundary by both
surface fold and lemma. Three synthetic pins prove these forms emit no verbal
universal and do not become arithmetic states.

**pytest 2,083 passed; scratch lint 0 errors with the same eight warnings;
curated 65/65 twice.** All eight standard DEV snapshot diffs and both grouped
FOLIO-with-logic diffs are NEUTRAL against reader 13 (0 BROKE, 0 DECL→WRONG);
the caught GSM8K item returns to decline. FOLIO outcomes, coverage, veto,
stack, collision, quarantine, agreement, ambiguity, and clause-split metrics
are unchanged. This is infrastructure only: reader count remains 13, no Phase
B movement is claimed, and no TEST look was spent.

**Next:** re-land reader 14's separately measured `CLSs will either V P or V2
Q` exact future-event disjunction now that its copular refusal is structural.
