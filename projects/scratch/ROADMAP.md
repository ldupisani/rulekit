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
| **A. Intersective decomposition of atoms** — shared `intersective_split` contract, top-level-nominal-only, composes with instantiation | this commit |

## Stage 1 — copular conditionals (the largest measured premise family)

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

## Stage 2 — decomposition siblings (more intersection-elimination)

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

## Stage 3 — disjunction, case analysis, exclusivity ("branching")

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

## Stage 4 — quantifier morphology and existentials

- `any`-universals ("Any choral conductor is a musician") — 'any' carries
  the article sense, so the rule needs its own reading; v2's named-next list.
- 'Each' universals; "Everyone who is P is Q" (pronoun-quantified copular).
- 'Some' existentials: `exis(P, Q)` facts + ∃-introduction
  (`atom(e,P) ∧ atom(e,Q) ⊢ "some P are Q"`), which also relaxes the
  fragment guard's 'some' veto for read sentences.

## Stage 5 — the gate back to FOLIO (only if/when wanted)

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
