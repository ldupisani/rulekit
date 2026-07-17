# The composition frontier — object-position substitution, designed before built

Status: **DESIGN — nothing here is implemented.** Written 2026-07-17, after
the cheap-increment closure (`6f876ce`): five deferred families all block on
the same missing capability, and this document is the required design for it
(ROADMAP.md → "The cheap-increment frontier is EXHAUSTED"). Every number
below was measured on folio dev-train with the scratch logic pack loaded;
nothing is estimated.

## 1. The capability, stated precisely

Substitute a fact about a verbal predicate's OBJECT into the predicate:

- **Membership bridge** (∃-introduction over the object):
  `rel(x, T) ∧ T ∈ CLS ⊢ ∃c. c ∈ CLS ∧ rel(x, c)` — answers
  *"does x ⟨verb⟩ ⟨prep⟩ **a** CLS?"* from a premise naming T.
  ("Ailton was loaned out to Braga" + "Braga is a football club" ⊢
  "Ailton was loaned out to A football club".)
- **Locative bridge** (upward-monotone containment):
  `rel_loc(x, A) ∧ in(A, B) ⊢ rel_loc(x, B)` — "lives in Manhattan" +
  "Manhattan is in New York City" ⊢ "lives in New York City".

Both are blocked today because a verbal atom's pred is ONE flat phrase key
(`'loan out to braga'`) — echo-exact by design, opaque to inference. The
Fiedler discipline (a key never loosens) is what made Stages 1–8 sound;
composition must NOT relax it. The design below never touches flat-key
matching: it adds a parallel STRUCTURED fact and does every bridge at query
time.

## 2. The design

### 2.1 No string surgery, anywhere — the one architectural rule

A derived flat key ("replace 'manhattan' with 'new york city' inside the
string") is forbidden. The ROADMAP already bans key surgery for relative
clauses ("the split at the UNIT level … never string surgery"); the same
rule governs here, for the same reason: a phrase key's segmentation is not
recoverable from its string ('play for square leg' — which words are the
object?). Segmentation happens ONLY where units still exist: in match
tokens, at read time.

### 2.2 A structured fact kind, emitted beside the flat atom

    VerbalRelation(entity, verb, prep, obj, polarity)
    # "Ailton plays for Náutico" -> VerbalRelation('ailton', 'play', 'for', 'náutico', +)

Emitted by a NEW premise-rule variant that segments the construction with
its own match tokens:

    - {slot: subj, type: name, at_start: true, blocks_skipped: indefinite_article}
    - {slot: v, type: nonstate_verb}
    - {slot: prep, type: preposition}
    - {slot: obj, span: true, span_blocks: [negation, disjunctive_marker, preposition]}

The flat atom from `logic/ground-verbal` is STILL emitted (rules coexist;
echo behavior is byte-identical — a contract test pins it). The structured
fact is strictly additive. `span_blocks: preposition` on obj keeps a second
PP out of the object ("plays for Náutico in Brazil" does not segment —
falls back to the flat atom only; whole-construction-or-nothing, the
Stage 1 rule).

### 2.3 Bridges run at QUERY time, in the consumer

New ask variants segment the conclusion the same way (unit-level, by match
tokens — `consume_skipped` claims the article exactly as Stage 4's
existential-verbal asks do):

    "Is it true that X was loaned out to a football club?"
      -> {entity: x, v: 'loan', prep: 'to', obj_cls: 'football club',
          obj_kind: 'indefinite', polarity: ...}

The consumer answers from VerbalRelation + the SATURATED class layer:

- **yes** ⟵ `VerbalRelation(x, v, prep, T, +)` where `atom(T, obj_cls, +)`
  holds (directly or via the saturated Quantified/decomposition chain —
  note "Náutico is a football club ALONG WITH Braga" yields
  atom('náutico', 'football club along with braga'), and **Stage 2.2's PP
  drop already derives the bare 'football club'** — the landed
  decomposition machinery is what makes the membership check reachable).
- **no** ⟵ only for the NEGATED indefinite question ("does not v prep a
  CLS"): a stored positive VerbalRelation whose T ∈ CLS contradicts the
  claimed ¬∃. The bare absence of a relation is never 'no' (open world).
- **undetermined** otherwise. Null control: swap CLS for an absent class —
  the answer must move.

Provenance in the reason string names the bridge witness:
`"via 'braga' ∈ 'football club'"`.

### 2.4 Soundness, per bridge

- **Membership bridge: sound for any verb, positive facts only.**
  ∃-introduction needs no monotonicity assumption about the verb — the
  premise itself supplies the witness. Negative premises license nothing
  (¬rel(x, T) says nothing about other members of CLS).
- **Locative bridge: gated twice, and Phase 2 only.** `rel_loc(x, A) ∧
  in(A, B) ⊢ rel_loc(x, B)` is sound only when (a) the preposition is
  spatial containment — gate on a new `containment_prep` category
  (members: 'in'; NOT 'for'/'with'/'about': "believes in Santa" + "Santa
  is in the mall" must never derive "believes in the mall"), and (b) the
  verb's event is located at its object — gate on a `locative_verb`
  category ('live', 'work', 'be born' …). Both category names are
  structure; members are pack data (constitution rule 1).

### 2.5 Phase 0 — a LIVE unsoundness this design surfaced (fix first)

Flat span keys drop articles, so the definite and indefinite readings
share one key — **measured today, committing a verdict**:

    "Rex plays for a football club. Is it true that Rex plays for THE
    football club?"  ->  yes   (via flat-key echo 'play for football club')

An indefinite premise answering a definite question is a wrong-in-waiting
(the definite asks about a particular club).

**BUILT (`725dd2c`) — and the built mechanism is deliberately NOT the
draft's.** The draft proposed a span flag making every definite question
decline; implementation analysis showed that kills two SOUND cells —
definite echo ("plays for the club" ×2) and definite-surfaced NAMES
("works at the Emmet Building", "holds the Lithuanian Super Cup") —
which folio conclusions use constantly. What landed instead enforces the
full matrix: `Atom.indef_obj` (emission-time bit, outside key(),
inherited by decomposition variants) × `patterns.field_definite_common`
(per ask FIELD; a 'the' whose next nominal past adjectives is a COMMON
noun — a name successor passes). Only the one unsound cell refuses.
Both checks cover the span's interior AND its physical leading edge —
the pre-token skip loop advances past leading skippables before a span
captures, so an internal scan alone misses exactly the copular
construction ("is A dog"); the walk-back is the blocks_skipped
precedent. Pinned in tests/test_article_compatibility.py (8 tests);
folio-with-logic item-level NEUTRAL, all 3 conversions survive.

## 3. What it buys — the measured stack table

**The bridge alone converts approximately nothing.** Every observed buyer
needs composition STACKED with one or two other pieces. Landing order must
follow the stacks, and a stage with no completed stack is an unbought
enabler (do not land it alone — the `_TOKEN` lesson).

| # | item (id, gold) | stack needed | pieces beyond this design |
|---|---|---|---|
| S1 | Ailton loaned-out (`3ef8a305b63c`, **False**) | rel-clause predication → passive normal form → membership bridge → negated-indefinite ask | subject-relative predication ("a football player WHO was loaned out to Braga" ⊢ the relation); passive participle ('was loaned out to') as a readable relation |
| S2 | Oxford designed-by (**True**) | active↔passive linking → membership bridge | "John Nash designed Oxford Circus" (active) must answer 'designed BY a British architect' (passive) — one voice-normalization rule, verb category `design`-class not needed (structural: by-agent ↔ subject) |
| S3 | Asa Hoffmann New Yorker (**True**) | 'People who/living in' universals → locative bridge | blocked separately by the corpus TYPO (Hoffmann/Hoffman — different keys; do not chase that item, the class may have other members) |
| S4 | mixer/Djokovic (**True/False**) | case analysis + conditional chains + verbal universal with PP-restricted class + bridge | deepest stack; not a target |

The honest reading: **S2 (passive linking + membership bridge) is the
shortest complete stack** — two increments, one measured buyer, both
pieces reusable by S1. S1 adds subject-relative predication (already the
`substring-bridge` class from the Stage 7 taxonomy, 2 measured items).
Build order: Phase 0 → VerbalRelation + membership bridge + passive
linking (S2, lands with its buyer) → relative-clause predication (S1's
last piece, lands against S1's item) → locative bridge only if a
post-S1/S2 re-measure shows a stack it completes.

**S2 is BUILT (`f192441`) and converted 2, not 1.** The stack needed a
piece the table missed: the buyer's story carried "Oxford Street and
Regent Street are in London" — an unread conjoined-subject copular whose
'and' made the fragment guard veto every verdict in the story. The fix
is `logic/ground-copular-conj-subjects` (distribution over both
conjuncts; the collective gate is the collective's own signal — 'are A
team' takes the indefinite article, refused on both the leading-edge and
interior article routes), which lifts the veto BY READING. That rule
then converted the story's second conclusion outright ("Regent Street is
not in London?" gold False, 'no' from the distributed atom). Both
conversions null-controlled. Folio-with-logic dev-train: 3 → 5 correct.
Lesson for S1: **walk the buyer's WHOLE story before sizing a stack —
the fragment guard prices every unread sentence into the item.**

## 4. Hazards designed out in advance (each becomes a pinned test)

1. **Definite/indefinite conflation** — Phase 0 above; pin both directions.
2. **The bridge must use the saturated + decomposed class layer** — the
   'along with' tail shows a direct-atom check misses real members; the
   test names the tail ("Braga is a football club along with X").
3. **State verbs stay out** — `nonstate_verb` on the v slot; "does not
   have an office in Germany" never reaches a bridge (possession is the
   fold's, the be-twin rule). 7 of 15 do-support items are 'have' — they
   are NOT this frontier's buyers and must not tempt a widening.
4. **Negative facts never bridge** — ¬rel(x,T) with T ∈ CLS licenses
   NOTHING about the class ("doesn't play for Braga" ⊬ "doesn't play for
   a football club"). Pin the non-derivation.
5. **A second PP never rides in the object span** (`span_blocks:
   preposition`) — "plays for Náutico in 1995" must not bind obj='náutico
   in 1995'; whole-construction-or-nothing.
6. **Diacritic-inconsistent corpus spellings** ('Náutico' premise vs
   'Nautico' conclusion — REAL in the Ailton story) — after the Unicode
   tokenizer fix these are DIFFERENT keys. If S1/S2's buyer items hit it,
   the candidate fix is diacritic-stripping in the FOLD only (surface
   preserved, 'café'-vs-'cafe' fold to one key) — measure its blast
   radius separately across all 7 corpora before landing; never patch
   per-item.
7. **Query-time cost** — bridges scan VerbalRelation × class-membership;
   both stores are per-item tiny (≤ dozens). No index needed; note only
   so nobody "optimizes" it into a materialized (surgery) form.

## 5. What must NOT be built (measured or ruled out this session)

- **Materialized derived keys** (§2.1) — string surgery, banned.
- **Locative bridge ungated** — "believes in" (§2.4).
- **'have'-possession bridging** (§4.3).
- **Unknown-plural morphology, bare-plural disjunctive premises,
  do-support asks as standalone increments** — all measured at zero
  (`6f876ce`); do-support returns only as S-stack conclusions' ask layer,
  landing WITH a completed stack.
- **A generic "paraphrase" matcher** (embedding-style loose matching) —
  the difg vocab_singles sin in new clothes; every bridge here is a
  NAMED, sound inference with a witness in its reason string.

## 6. Gate plan (unchanged discipline)

Each phase: one revertible commit; synthetic contract tests written
FIRST (never a corpus string); full six-corpus gate (all byte-neutral —
the pack stays scratch-scoped, VerbalRelation is emitted by no benchmark
rule); folio-with-logic re-measured with `rulekit diff` (+N SOLVED /
0 BROKE required); every new commit null-controlled (swap the bridge
witness's class, cut either premise — the answer must move). DEV looks
are free; folio TEST stays governed by the Stage 5 closure rules — the
~10–30 null-controlled-commit precondition still stands, and this
frontier is how the count grows.
