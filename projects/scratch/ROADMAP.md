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
