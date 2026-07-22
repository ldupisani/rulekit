> **Active direction (2026-07-21): Delphi breadth-first premise readers.**
> Phase A is complete: the reproducible DEV-only baseline is
> [`../projects/scratch/folio-blocker-baseline.json`](../projects/scratch/folio-blocker-baseline.json),
> its interpretation and look-#6 thresholds are in
> [`../projects/scratch/ROADMAP.md`](../projects/scratch/ROADMAP.md), and the campaign plan is
> [`delphi-learnings-plan.md`](delphi-learnings-plan.md). Phase B readers 1–50 now serve
> ground both-or-neither equivalence, unrestricted bare-plural disjunction, negative
> two-article indefinite generics, single-antecedent verbal “Everyone who” implications,
> verbal-restrictor `If a CLS V P, then it is Q` conditionals, (reader 6)
> the negative-antecedent same-entity ground conditional `If NAME is not P, then NAME
> is Q` via a dedicated `GroundConditional` fact + unless-free fire synth — the
> contrapositive comes FREE through the 9i reductio engine (pinned). The initially
> landed literal-`he` surface was removed after review: without resolved coreference it
> could misbind `he` to the antecedent subject when another name occurred inside the
> predicate — and (reader 7) the plural generic `If people are P, then they are [not]
> Q`, using the existing `Quantified` fact and instantiation synth — and (reader 8)
> class-scoped `CLSs who are P are [not] Q`, using the existing `Conditional` fact —
> and (reader 9) restricted `Everyone RESTRICTION is [either] L or R`, using the
> existing `QuantifiedDisjunction` fact and instantiation/case-analysis synths —
> and (reader 10) two-article indefinite-generic disjunctions `A/An CLS is
> either a/an L or a/an R`, reusing the same fact and synth path — and
> (reader 11) negative possessive universals `No CLSs have P` / `No CLS has
> P`, using negative `Quantified` facts and the existing chain/instantiation
> synths — and (reader 12) plural-agreeing negative event universals `No
> CLSs V P`, again using negative `Quantified` facts and the existing
> chain/instantiation synths — and (reader 13) named ground do-support event
> denials `NAME does not V P`, using exact negative `Atom` keys and the existing
> verdict consumer — and (reader 14) bare-plural future-event disjunctions
> `CLSs will either V P or V2 Q`, using exclusive `QuantifiedDisjunction` facts
> and the existing instantiation/elimination synths — and (reader 15)
> future-negative indefinite generics `A/An CLS will not V P`, using negative
> `Quantified` facts and existing chaining/instantiation — and (reader 16)
> mixed named possession/event disjunctions `NAME has P or V Q`, using an
> inclusive ground `Disjunction` — and (reader 17) singular positive possessive
> universals `Every CLS has P`, using positive `Quantified` facts — and
> (reader 18) plural-generic copular-to-verbal conditionals `If people are P,
> then they V Q`, again using positive `Quantified` facts — and (reader 19)
> indefinite-generic verbal conditionals `If a/an CLS V P, [then] they V2 Q`
> — and (reader 20) reduced-relative people universals `People V P are Q`,
> with a one-unit capitalized plural predicate folded consistently through
> the existing plural-agreement contract — and (reader 21) fully repeated
> `NAME is either both A and B or neither A nor B` equivalences, guarded by
> exact repeated-span equality — and (reader 22) implicit-restrictor property
> universals `Anything P is Q` / `No one P is Q`, using positive/negative
> `Quantified` facts — and (reader 23) second-person generic conditionals
> `If you are a P, then you are a Q`, using a positive `Quantified` fact —
> and (reader 24) missing terminal boundaries between a wholly read premise
> and a wholly read ask — and (reader 25) active reduced-relative possessive
> universals `Everyone V-ing P has Q`, guarded by opt-in present-participle
> morphology and emitted as `Quantified(V(P), have(Q))` — and (reader 26)
> plural-agreeing positive possessive universals `All CLSs have P`, using
> positive `Quantified` facts and the existing negative-chain path — and
> (reader 27) comma-bound free-relative verbal conditionals `If a/an CLS V P,
> they V2 what SUBJECT V3 Q`, preserving the embedded clause inside one exact
> consequence key — and (reader 28) inclusive two-article indefinite-generic
> disjunctions `A/An CLS is a/an L or a/an R`, reusing
> `QuantifiedDisjunction` with bare-`or` semantics — and (reader 29)
> active-participial compound verbal universals `V-ing CLSs V2 P`, using
> exact participial class keys — and (reader 30) named-PP existential premises
> `There is a/an CLS PREPOSITION NAME`, using `Existential` without minting a
> witness — and (reader 31) direct passive named-agent premises `The PATIENT
> is V-ed by NAME`, using a morphology-gated `VerbalRelation(NAME, V,
> PATIENT)` — and (reader 32) PP-restricted negative verbal universals `None
> of the CLSs PREPOSITION R V the P`, using exact negative `Quantified`
> facts — and (reader 33) reversed named memberships `One of the CLSs of
> OWNER was MEMBER`, emitting the identified witness as an exact positive
> `Atom(MEMBER, CLS+of+OWNER)` — and (reader 34) exactly-three named
> distributive copular subjects `A, B[, ] and C are P`, emitting one exact
> positive `Atom` per name while refusing collective predicates — and
> (reader 35) reversed definite role memberships `The ROLE of OWNER is/was
> MEMBER`, preserving the full owner-qualified role key — and (reader 36)
> exactly-four asyndetic named copular lists `A, B, C, D are P`, distributing
> the singular-folded predicate over all four names — and (reader 37) past
> indefinite existentials `There was a/an CLS PREPOSITION the DESCRIPTION`,
> preserving the qualified definite PP without minting a witness — and
> (reader 38) definite-description ground memberships `The DESCRIPTION is
> a/an PREDICATE`, emitting one exact `Atom` for the described referent — and
> (reader 39) definite-description memberships with reduced passive relatives
> `The DESCRIPTION is a/an CLS V-ed REST`, emitting both entailed base-class
> membership and the exact restricted property — and (reader 40) restricted
> plural-generic verbal conditionals `If people RESTRICTION V P, then they V2 Q`,
> reusing `Conditional` for the restriction/event antecedent pair — and
> (reader 41) reduced-passive `Everything V-ed R is either a/an L or a/an R`
> exclusive universals, using productive morphology and nominal branch gates — and
> (reader 42) implicit-restrictor negative possession `Nothing R has P`, using
> an exact negative `Quantified(R, have P)` fact — and (reader 43)
> implicit-restrictor property universals `Everything P is Q`, using an exact
> positive `Quantified(P, Q)` fact — and (reader 44) appositive-restricted
> plural possession disjunctions `CLSs R, APPOSITIVE have either a L or a R`,
> preserving the full class and both nominal possession keys — and (reader 45)
> reduced-passive possessive existentials `Some CLSs V-IRREG by AGENT have P`,
> preserving the complete restricted witness class without minting a witness —
> and (reader 46) bare-name indefinite possession `NAME has a/an MODIFIER NOUN`,
> emitting the exact ground `have` Atom needed by possession conditionals while
> refusing article-marked subjects and larger object phrases — and (reader 47)
> positive same-name possession conditionals `If NAME has P, then NAME is Q`,
> using a dedicated positive ground implication that fires only from an exact
> positive Atom — and (reader 48) plural-agreeing intransitive existentials
> `Some CLSs VERB`, using the existing `Existential` fact and consumer without
> inventing an object — and (reader 49) restricted past-passive existentials
> `Some CLSs RESTRICTION were V-ed REST`, preserving both complete keys — and
> (reader 50) modal-passive existentials `Some CLSs can be V-ed REST`, retaining
> possibility inside the exact property rather than asserting actuality.
> A subsequent pack-scoped lexical activation (`act/acts`, `prevent`) makes
> the pre-existing Stage 9f verbal existential reader reachable for one train
> premise; it earns movement but no new construction-class credit.
> Cumulative movement from Phase A is +90 / +74 fully-read premise instances
> and +11 / +10
> stack-ready stories on dev-train / dev-holdout, with no
> verdict regression or hazard increase; truth-scope vetoes improve by 70 / 48, while
> holdout collision/quarantine improve 12→9 / 24→18. Forty-nine construction classes
> are served. Both stack-ready thresholds are now met, but the conjunctive Phase C
> gate remains unmet (fully read 810/1647 and 795/1607 vs 852/850; vetoes 596/566
> vs ≤499/460; stack-ready stories 22/15 vs ≥22/10).
> Next regenerate the fully-read and truth-scope-veto frontier, prioritizing
> train-side movement. The
> remaining candidates require lexical, definite-description, coreference,
> or deeper composition infrastructure. The unbought outer-quantified verbal
> relative remains banked pending composition evidence. Reader 4's opt-in
> `single_word` slot gate stays dormant for all pre-existing rules.
> The one-unit-span `_naive_singular` bank is now bought by reader 20;
> CamelCase-name and verbal-universal-ask banks still have zero joins.
> Reader 14 falsification also bought a prerequisite category correction:
> `state` is now the arithmetic-holding subclass of `non_event_verb`, and
> difg-mined's `be`/`been`/`being` join only the broader reader-exclusion
> category. This closes the bare-copula event-reader hole without changing
> arithmetic state semantics; it earns no reader or coverage credit.
> Reader 14's tense skeleton is now literal `will`, not the broader
> `future_modal` slot type (which also accepts ordinary auxiliaries for asks);
> do-support disjunctions therefore remain unread.
> ⚠ The regenerated movement classifier reproduces every recorded metric and all reader
> deltas exactly except a constant fully-read offset (−4/−11) — see the reader-6 ROADMAP
> record before comparing absolute totals. No TEST look was spent.
>
> **Campaign status (2026-07-20): PARKED.** The difg/SciBench physics-formula
> campaign is preserved in [`parked-physics-campaign.md`](parked-physics-campaign.md)
> at commit `5b9d62c`. Resume from that guide only when this direction is chosen
> again; the sessions below remain the detailed historical record.

# Session 66 (2026-07-22): Phase B reader 50 — modal-passive existentials; +1 train fully read and −1 veto

Reader 50 serves **“Some CLSs can be V-ed REST.”** The modal remains inside
the exact property key, so possibility never becomes actuality. A bare-plural
class proves number, and opt-in productive participle morphology proves passive
voice. The reader emits the existing positive `Existential`; its exact ask twin
uses the existing consumer. Singular, qualified, modal-free, other-modal,
negative, active, coordinated, bare-participle, counted, empty-rest, and
missing-boundary siblings remain unread. The qualified train candidate is
explicitly banked: noun condensation records its modifier as a qualifier, and
`bare_plural` intentionally refuses qualified/count/possessive noun units;
`can` supplies no independent agreement evidence. The buyer adds only the
pack-scoped `spotted → spot` morphology.

Eighteen synthetic pins cover exact emission and composition, modality versus
actuality, a changed-property null, and fourteen adjacent refusals. **All 2,723
tests pass; scratch lint has 0 errors and the same eight warnings; curated is
65/65 with an identical fresh-process rerun.** All eight standard DEV diffs
and both grouped logic diffs are NEUTRAL. Outcomes remain train 21 correct / 1
pre-existing poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1360→1361 (+1) | 809→810 (+1) | 28/22→28/22 | 3 / 1 | 597→596 (−1) |
| dev-holdout | 1330→1330 | 795→795 | 22/15→22/15 | 0 / 0 | 566→566 |

The sole buyer emits `Existential(turtle, can be spot near campus)`, becomes
fully read, and loses its veto. Other unread premises prevent stack movement.
Cumulative recorded-frame state is 810/1647 and 795/1607 fully read, 596/566
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Fifty classes are served. No TEST look was spent.

**Next:** regenerate the fully-read/truth-scope-veto frontier, prioritizing
train-side movement without weakening the qualified-noun refusal contract.

---

# Session 65 (2026-07-22): Phase B reader 49 — restricted past-passive existentials; +1 train fully read and −1 veto

Reader 49 serves **“Some CLSs RESTRICTION were V-ed REST.”** `Some` and the
plural-only copula `were` license singular folding of the complete restricted
class; opt-in productive past-participle morphology proves passive voice. The
full post-participle property remains exact and tense-normalized. It emits the
existing positive `Existential` fact, and a matching ask reaches the existing
consumer. Active, copular, present-passive, singular, modal, signed,
coordinated, bare-participle, counted-class, empty-rest, and missing-boundary
siblings remain unread. The buyer adds only pack-scoped
`established → establish` morphology.

Sixteen synthetic pins cover complete restricted emission, exact ask
composition, a changed-restriction null, and thirteen adjacent refusals. **All
2,705 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 with an identical fresh-process rerun.** All eight standard
DEV diffs and both grouped logic diffs are NEUTRAL. Outcomes remain train 21
correct / 1 pre-existing poisoned-text wrong / 472 declined and holdout 4 / 0
/ 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1359→1360 (+1) | 808→809 (+1) | 28/22→28/22 | 2 / 1 | 598→597 (−1) |
| dev-holdout | 1330→1330 | 795→795 | 22/15→22/15 | 0 / 0 | 566→566 |

The sole buyer is one train premise shared by two verdict rows. It emits
`Existential(federal district in russia, establish in 2000)`, becomes fully
read, and loses its veto. Other unread premises prevent stack movement.

Cumulative recorded-frame state is 809/1647 and 795/1607 fully read, 597/566
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-nine classes are served. No TEST look was spent.

**Next:** continue the regenerated fully-read/veto frontier, prioritizing
train-side buyers without reopening banked scope-ambiguous universals.

---

# Session 64 (2026-07-22): Phase B reader 48 — intransitive verbal existentials; +1 train fully read and −1 veto

Reader 48 serves **“Some CLSs VERB.”** `Some` supplies existence, one
bare-plural class plus one single-token bare non-state verb prove plural
agreement, and the immediate terminal period closes an intransitive predicate
without inventing an object. It emits the existing positive
`Existential(CLS, VERB)` fact; the matching question-side twin reaches the
existing existential consumer. Transitive, copular, stative, modal, passive,
signed, coordinated, restricted-class, counted, singular, other-tense, and
missing-boundary siblings remain unread. The buyer adds only pack-scoped
`sophist/sophists` and `reason` morphology.

The regenerated frontier also reconsidered `All CLSs are not PROPERTY` and
rejected it before implementation: the ROADMAP's earlier v1 falsification
already records mixed FOLIO scope judgments and a confident wrong from that
broad reader. It remains banked.

Fifteen synthetic pins cover exact emission, exact ask composition, a changed-
event null, and twelve adjacent refusals. **All 2,689 tests pass; scratch lint
has 0 errors and the same eight warnings; curated is 65/65 with an identical
fresh-process rerun.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing poisoned-
text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1358→1359 (+1) | 807→808 (+1) | 28/22→28/22 | 2 / 1 | 599→598 (−1) |
| dev-holdout | 1330→1330 | 795→795 | 22/15→22/15 | 0 / 0 | 566→566 |

The sole buyer is one train premise shared by two verdict rows. It gains the
direct existential fact, becomes fully read, and loses its veto. Independent
unread premises keep the story out of the stack-ready set.

Cumulative recorded-frame state is 808/1647 and 795/1607 fully read, 598/566
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-eight classes are served. No TEST look was spent.

**Next:** continue the regenerated frontier; keep the negative `All … are not
…` family banked unless a representation can encode its surface scope without
reintroducing the recorded confident wrong.

---

# Session 63 (2026-07-22): Stage 9f lexical activation — +1 train fully read and −1 veto; no new class

The regenerated post-Reader-47 frontier found that the existing Stage 9f
reader and ask already define the safe construction **“Some CLSs VERB
OBJECT.”** Its `Some Acts prevent harmful things` train buyer was dormant only
because `act/acts` and bare `prevent` were absent from the logic-pack lexicon,
causing premise and ask rendering to disagree and leaving the verb structurally
unknown. This increment adds only those two pack-scoped morphology facts. It
does not widen a rule, add a synth, or earn construction-class credit.

Four synthetic pins cover exact existing-reader emission, its existing ask
twin, a changed-object null, and singular-agreement refusal. **All 2,674 tests
pass; scratch lint has 0 errors and the same eight warnings; curated is 65/65
with an identical fresh-process rerun.** All eight standard DEV diffs and both
grouped logic diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-
existing poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1357→1358 (+1) | 806→807 (+1) | 28/22→28/22 | 2 / 1 | 600→599 (−1) |
| dev-holdout | 1330→1330 | 795→795 | 22/15→22/15 | 0 / 0 | 566→566 |

The one train premise now emits the pre-existing exact
`Existential(act, prevent harmful things)`, becomes fully read, and loses its
veto across two verdict rows in one story. Independent unread premises keep
the story out of the stack-ready set. No holdout sentence uses this lexical
pair.

Cumulative recorded-frame state is 807/1647 and 795/1607 fully read, 599/566
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-seven construction classes remain served. No TEST look was spent.

**Next:** continue the regenerated frontier, keeping lexical activations
separate from new construction readers and prioritizing train movement.

---

# Session 62 (2026-07-22): Phase B reader 47 — positive ground possession conditionals; +1 holdout fully read and −1 veto

One reader serves **“If NAME has [a/an] PROPERTY, then NAME is a/an
PROPERTY.”** Repeated bare proper names prove the same ground entity; `has`
canonicalizes the antecedent to an exact `have PROPERTY` key, and the optional
object article is grammatical skeleton rather than predicate content. A new
`PositiveGroundConditional` keeps this positive-antecedent construction
separate from Reader 6's deliberately negative-only `GroundConditional`.
Its synth fires only from an explicit positive Atom with the complete key and
retains the no-`unless` collision/reductio discipline. Internal nominal
coordination is preserved atomically, never distributed. Signed, modal,
disjunctive, cross-name, pronominal-consequent, verbal-consequent, and missing-
boundary siblings remain unread.

Nineteen synthetic pins cover exact emission, Reader 46 composition, an
undecided antecedent, a changed-property null, and fifteen adjacent refusals.
**All 2,670 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 with an identical fresh-process rerun.** All eight standard
DEV diffs and both grouped logic diffs are NEUTRAL. Outcomes remain train 21
correct / 1 pre-existing poisoned-text wrong / 472 declined and holdout 4 / 0
/ 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1357→1357 | 806→806 | 28/22→28/22 | 0 / 0 | 600→600 |
| dev-holdout | 1329→1330 (+1) | 794→795 (+1) | 22/15→22/15 | 8 / 1 | 567→566 (−1) |

The sole buyer is Sam's positive possession conditional, shared by eight
holdout verdict rows in one story and absent from train. It gains the new fact,
becomes fully read, and loses its veto. Other unread generic/modal premises
keep that story out of the stack-ready set. Reader 46's exact `have` Atom
composition is pinned synthetically; the measured buyer has no matching ground
antecedent in its story, so no verdict changes.

Cumulative recorded-frame state is 806/1647 and 795/1607 fully read, 600/566
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-seven classes are served. No TEST look was spent.

**Next:** regenerate the fully-read/truth-scope-veto frontier, prioritizing a
train-side buyer.

---

# Session 61 (2026-07-22): Phase B reader 46 — named indefinite possession; +1 holdout fully read and −1 veto

One reader serves **“NAME has a/an MODIFIER NOUN.”** Bare proper-name subject,
singular `has`, an overt object article, one noun-category compound, and the
terminal period emit an exact positive `Atom(NAME, have MODIFIER NOUN)`. The
noun renders through its surface so modifiers survive. A matching ask reaches
the existing logic-verdict consumer. Article-marked/common/pronominal subjects,
signed/modal/other-tense possession, articleless/plural/counted objects,
coordination, disjunction, larger object phrases, appositives, and missing
boundaries remain unread. The narrow compound gate also avoids treating a
skipped internal comma as a safe span boundary.

Eighteen synthetic pins cover complete emission, exact ask composition, a
changed-property null, and fifteen adjacent refusals. **All 2,651 tests pass;
scratch lint has 0 errors and the same eight warnings; curated is 65/65 with an
identical fresh-process rerun.** All eight standard DEV diffs and both grouped
logic diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1357→1357 | 806→806 | 28/22→28/22 | 0 / 0 | 600→600 |
| dev-holdout | 1329→1329 | 793→794 (+1) | 22/15→22/15 | 1 / 1 | 568→567 (−1) |

The holdout-only Adam premise already had a generic fact, so fact-bearing does
not move; consuming the complete possession construction makes it fully read
and removes its truth-scope veto. Another premise in that story remains unread,
so stack readiness does not move. Reader 46 also supplies the exact ground Atom
schema required for a future named-possession conditional composition pin.

Cumulative recorded-frame state is 806/1647 and 794/1607 fully read, 600/567
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-six classes are served. No TEST look was spent.

**Next:** price the named-possession conditional against DEV; bank it if the
composition prerequisite has no measured buyer.

---

# Session 60 (2026-07-22): Phase B reader 45 — reduced-passive possessive existentials; +3 holdout fully read and −3 vetoes

One reader serves **“Some CLSs V-IRREG by AGENT have a/an PROPERTY.”** `Some`
supplies existence, plural noun morphology bounds and folds the witness class,
and an opt-in irregular-past-participle category proves the reduced passive.
The full by-agent phrase remains inside the exact class key; bare stative
`have` and the required object article delimit the possession predicate. No
witness is invented. A matching question-side reader routes exact existential
queries to the existing consumer. Signed, singular, finite, productive,
active, modal, coordinated, counted, articleless, other-agreement, and
missing-boundary siblings remain unread.

The measured buyer completes the existing shared `monitor` noun entry with
plural `monitors`; the pack-scoped irregular-participle category initially
contains only `made`. Bare `make` cannot join. Eighteen synthetic pins cover
complete restricted emission, exact existential echo, a changed-agent null,
and fifteen adjacent refusals. **All 2,633 tests pass; scratch lint has 0
errors and the same eight warnings; curated is 65/65 with an identical fresh-
process rerun.** All eight standard DEV diffs and both grouped logic diffs are
NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing poisoned-text wrong
/ 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1357→1357 | 806→806 | 28/22→28/22 | 0 / 0 | 600→600 |
| dev-holdout | 1326→1329 (+3) | 790→793 (+3) | 22/15→22/15 | 3 / 3 | 571→568 (−3) |

The same monitor premise occurs in four holdout verdict rows across three
distinct stories and no train story. All three premise instances gain direct
facts, become fully read, and lose their truth-scope veto. The independent
second premise remains unread, so stack readiness does not move. Outcomes and
hazards remain neutral.

Cumulative recorded-frame state is 806/1647 and 793/1607 fully read, 600/568
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-five classes are served. No TEST look was spent.

**Next:** regenerate the post-Reader-45 frontier; both fully-read and veto
thresholds remain conjunctively binding.

---

# Session 59 (2026-07-22): Phase B reader 44 — appositive-restricted plural possession disjunctions; +6 train fully read and −6 vetoes

One reader serves **“CLSs RESTRICTION, APPOSITIVE have either a/an MODIFIER
NOUN or a/an MODIFIER NOUN.”** Plural morphology licenses the singular class
fold; both required spans around the appositive comma remain in its exact key,
and overt articles plus noun-category compound units prove the two possession
branches. The noun compounds render through their complete surfaces, so their
modifiers are not lost. Signed, comma-free or empty-appositive, verbal, modal,
coordinated, counted, articleless, larger, and missing-boundary siblings remain
unread.

The measured buyer required three pack-scoped lexical entries (`lipstick` as
a noun with plural `lipsticks`; `velvet` and `satin` as adjectives) and one
shared correction: `finish` is genuine noun/verb polysemy rather than
verb-only. The article context selects its noun sense. The shared correction
is neutral across all standard gates.

Nineteen synthetic pins cover exact complete-key emission, quantified-
disjunction instantiation, a changed-restriction null, and sixteen adjacent
refusals. **All 2,615 tests pass; scratch lint has 0 errors and the same eight
warnings; curated is 65/65 with an identical fresh-process rerun.** All eight
standard DEV diffs and both grouped logic diffs are NEUTRAL. Outcomes remain
train 21 correct / 1 pre-existing poisoned-text wrong / 472 declined and
holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1351→1357 (+6) | 800→806 (+6) | 28/22→28/22 | 6 / 6 | 606→600 (−6) |
| dev-holdout | 1326→1326 | 790→790 | 22/15→22/15 | 0 / 0 | 571→571 |

The same lipstick premise occurs in seven verdict rows across six distinct
train stories and no holdout story. Each story's premise gains a direct
fact, becomes fully read, and loses its truth-scope veto. Other unread
premises keep stack readiness unchanged. Outcomes and hazards remain neutral.

Cumulative recorded-frame state is 806/1647 and 790/1607 fully read, 600/571
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-four classes are served. No TEST look was spent.

**Next:** regenerate the post-Reader-44 frontier; both fully-read and veto
thresholds remain conjunctively binding.

---

# Session 58 (2026-07-22): Phase B reader 43 — Everything copular universals; +2 train fully read and −2 vetoes

One reader serves **“Everything RESTRICTION is PROPERTY.”** `Everything`
supplies the universal variable, while required nonempty bounded spans preserve
the exact restriction and consequence as a positive `Quantified` fact. Signed,
coordinated, disjunctive, verbal, modal, counted, empty-restriction,
other-copula, and missing-boundary siblings remain unread.

Seventeen synthetic pins cover exact emission, instantiation, a
changed-restriction null, and fourteen adjacent refusals. **All 2,596 tests
pass; scratch lint has 0 errors and the same eight warnings; curated is 65/65
with an identical fresh-process rerun.** All eight standard DEV diffs and both
grouped logic diffs are NEUTRAL. Outcomes remain train 21 correct / 1
pre-existing poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1349→1351 (+2) | 798→800 (+2) | 28/22→28/22 | 2 / 2 | 608→606 (−2) |
| dev-holdout | 1326→1326 | 790→790 | 22/15→22/15 | 0 / 0 | 571→571 |

The solar-system premise occurs in three train rows / two distinct stories
and no holdout rows. Both premise instances gain direct facts, become fully
read, and lose their truth-scope veto. Independent unread premises keep both
stories out of the stack-ready set. Outcomes and hazards remain neutral.

Cumulative recorded-frame state is 800/1647 and 790/1607 fully read, 606/571
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-three classes are served. No TEST look was spent.

**Next:** regenerate the post-Reader-43 frontier; both fully-read and veto
thresholds remain conjunctively binding.

---

# Session 57 (2026-07-22): Phase B reader 42 — restricted Nothing possession; +2 train fully read and −2 vetoes

One reader serves **“Nothing RESTRICTION has P.”** `Nothing` supplies the
universal variable, the required nonempty restriction is preserved as the
exact class key, and singular `has` fixes the negative consequence to
`have P`. Negation, quantifiers, scalar values, coordination, disjunction,
verbs, and modals are blocked inside spans; counted, signed, empty-restriction,
other-agreement, other-tense, and missing-boundary siblings remain unread.

Seventeen synthetic pins cover exact negative emission, instantiation, a
changed-restriction null, and fourteen adjacent refusals. **All 2,579 tests
pass; scratch lint has 0 errors and the same eight warnings; curated is 65/65
with an identical fresh-process rerun.** All eight standard DEV diffs and both
grouped logic diffs are NEUTRAL. Outcomes remain train 21 correct / 1
pre-existing poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1347→1349 (+2) | 796→798 (+2) | 28/22→28/22 | 2 / 2 | 610→608 (−2) |
| dev-holdout | 1326→1326 | 790→790 | 22/15→22/15 | 0 / 0 | 571→571 |

The identical solar-system premise occurs once in each of two distinct train
stories, covering three rows total (two verdict golds and one `Uncertain`).
Both premise instances gain a direct fact, become fully read, and lose their
truth-scope veto. Other unread premises keep both stories out of the
stack-ready set. Outcomes and hazards remain neutral.

Cumulative recorded-frame state is 798/1647 and 790/1607 fully read, 608/571
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-two classes are served. No TEST look was spent.

**Next:** regenerate the post-Reader-42 frontier; both fully-read and veto
thresholds remain conjunctively binding.

---

# Session 56 (2026-07-22): Phase B reader 41 — reduced-passive Everything disjunction; +1 train fully read and −1 veto

One reader serves **“Everything V-ed RESTRICTION is either a/an L or a/an
R.”** `Everything` supplies the universal variable; a productive, single-token
past participle proves the reduced-relative boundary, and the complete
restriction becomes the exact class key. Both overt predicate articles plus
noun-category units prove the exclusive nominal branches. Bare, finite,
present-participial or irregular verbs, empty restrictions, other copulas,
articleless/signed/coordinated/count-bearing branches, larger disjunctions,
and missing boundaries remain unread.

The logic pack adds only `displayed → display` as a verb: the mined bare
`display` remains noun-only, while the overt `-ed` surface now satisfies the
existing participle gate. The mined lexicon already contains `plant` as real
noun/verb polysemy, so the branch's article and noun-category gate select its
noun role without another override.

Nineteen synthetic pins cover exact emission, instantiation/elimination
composition, a changed-restriction null, and sixteen adjacent refusals.
**All 2,562 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 with an identical fresh-process rerun.** All eight standard
DEV diffs and both grouped logic diffs are NEUTRAL. Outcomes remain train 21
correct / 1 pre-existing poisoned-text wrong / 472 declined and holdout 4 / 0
/ 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1346→1347 (+1) | 795→796 (+1) | 28/22→28/22 | 2 / 1 | 611→610 (−1) |
| dev-holdout | 1326→1326 | 790→790 | 22/15→22/15 | 0 / 0 | 571→571 |

Across all gold kinds the reader occurs in three train rows / one story and
no holdout rows. The collection-display premise is the sole new direct fact,
fully-read premise, and consumed truth-scope veto. Other unread constructions
in the story keep stack readiness unchanged. Outcomes and hazards are neutral.

Cumulative recorded-frame state is 796/1647 and 790/1607 fully read, 610/571
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty-one classes are served. No TEST look was spent.

**Next:** regenerate the post-Reader-41 frontier; fully-read and veto targets
remain conjunctively binding on both splits.

---

# Session 55 (2026-07-22): Reader 39 correction — preserve noun “building” instead of verb lemma “build”

Review found that Reader 39 correctly gated its class slot with `cat: noun`
but rendered the slot through the default ambiguous-unit lemma. Consequently,
the noun **“building”** emitted the verb key `build`; the synthetic expectation
had encoded that bug. The premise now renders the noun surface in both its
base-class and reduced-relative atoms: `building` and `building add …`.

The fix is symmetric on the question side. A narrow reduced-passive copular
ask mirrors Reader 39's noun-category and productive-participle gates and
renders the same noun surface, so an exact question joins the corrected fact
instead of continuing to ask for `build add …`. The general copular ask and
all other ambiguous-unit rendering remain unchanged.

The corrected exact-emission and composition pins pass. **All 2,543 tests
pass; scratch lint has 0 errors and the same eight warnings; curated is 65/65
with an identical fresh-process rerun.** All eight standard DEV diffs and both
grouped logic diffs are NEUTRAL. Coverage, veto, stack, outcome, and hazard
metrics remain exactly at the Reader 40 frame. No TEST look was spent.

**Next:** resume the train-side fully-read/truth-scope-veto frontier from the
clean Reader 40 baseline.

---

# Session 54 (2026-07-22): Phase B reader 40 — restricted people verbal conditionals; +1 holdout fully read and −1 veto

One reader serves **“If people RESTRICTION V P, then they V2 Q.”** The
nonempty restriction and antecedent event become the two antecedent properties
of the existing `Conditional` fact; both event heads require bare plural
agreement and one original token. The exact consequence reuses existing
conditional instantiation. Signed, modal, coordinated, copular, unrestricted,
comma-only, counted, multi-verb, and missing-boundary siblings remain unread.

Seventeen synthetic pins cover exact emission, two-antecedent composition, a
missing-antecedent null, and fourteen adjacent refusals. Two broader candidates
were surveyed and banked first: the same verbal skeleton had no train buyer,
and articleless indefinite disjunctions initially matched five premises but
could not structurally refuse an ambiguous finite-verb branch without also
losing every buyer. **All 2,543 tests pass; scratch lint has 0 errors and the
same eight warnings; curated is 65/65 with an identical fresh-process rerun.**
All eight standard DEV diffs and both grouped logic diffs are NEUTRAL.
Outcomes remain train 21 correct / 1 pre-existing poisoned-text wrong / 472
declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1346→1346 | 795→795 | 28/22→28/22 | 0 / 0 | 611→611 |
| dev-holdout | 1325→1326 (+1) | 789→790 (+1) | 22/15→22/15 | 2 / 1 | 572→571 (−1) |

Across all gold kinds the reader appears in three holdout rows / one story and
no train rows. The Mary's-school ordering premise supplies the sole new direct
fact, fully-read premise, and consumed truth-scoping conditional. Its story
still contains several independent unread constructions, so stack readiness
does not move. Outcomes and all hazards remain neutral.

Cumulative recorded-frame state is 795/1647 and 790/1607 fully read, 611/571
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Forty classes are served. No TEST look was spent.

**Next:** regenerate the frontier and prioritize a train-side fully-read/veto
buyer; the stack thresholds remain satisfied but the conjunctive Phase C gate
is still closed.

---

# Session 53 (2026-07-22): Phase B reader 39 — reduced-passive definite membership; +1 train fully read and stack-ready story

One reader serves **“The DESCRIPTION is a/an CLS V-ed REST.”** The predicate
article and noun-category gate prove the base class even when the unit is
lexically ambiguous (`building`); the opt-in productive past-participle gate
proves the reduced-relative boundary. The construction emits the two positive
atoms it entails: base `CLS` membership and the exact `CLS V REST` restriction.
It invents neither an event nor an identity. Sign, coordination, finite/bare
verbs, auxiliary passives, irregular participles outside the productive gate,
further clauses, missing tails, and missing boundaries remain unread.

Nineteen synthetic pins cover both exact emissions, exact-membership question
composition, a changed-description null, and sixteen adjacent refusals. The
first grouped probe exposed a shadowing regression on “The Astro is a van
produced by Chevrolet”: the specific reader suppressed the older broad
copular reader's derived base membership. Emitting the independently entailed
base-class atom repaired that regression. **All 2,526 tests pass; scratch lint
has 0 errors and the same eight warnings; curated is 65/65 with an identical
fresh-process rerun.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1346→1346 | 794→795 (+1) | 27/21→28/22 (+1/+1) | 6 / 2 | 611→611 |
| dev-holdout | 1325→1325 | 789→789 | 22/15→22/15 | 0 / 0 | 572→572 |

Across all gold kinds the reader appears in seven train rows / two stories
and no holdout rows. The Chevrolet premise was already fully read and remains
behaviorally identical. The Blake McFall premise supplies the sole fully-read
gain; its represented `6a527cece7da` conclusion gains the last premise reader
and becomes stack-ready. The sibling location query retains its separate
paraphrase gap, and the remaining sibling is `Uncertain` text gold.

Cumulative recorded-frame state is 795/1647 and 789/1607 fully read, 611/572
truth-scope vetoes, 22/15 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-nine classes are served. Both stack thresholds are met, but the
fully-read and veto thresholds still bind conjunctively; no TEST look was
spent.

**Next:** regenerate and rank the frontier by fully-read and truth-scope-veto
movement. Meeting the final stack target does not schedule look #6.

---

# Session 52 (2026-07-22): Phase B reader 38 — definite-description ground membership; +2/+4 fully read, +1 train stack-ready story

One reader serves **“The DESCRIPTION is a/an PREDICATE.”** The leading
definite article denotes one described referent, so the rule emits a positive
`Atom(singular DESCRIPTION, PREDICATE)` rather than the `Quantified` fact used
by two-indefinite generics. Both articles, singular copula, bounded spans, and
terminal period prove the complete construction. A subject cardinal remains
inside its exact key; counted predicates, sign, coordination, relatives,
other copulas, verbal predicates, and missing boundaries remain unread.

Sixteen synthetic pins cover exact emission, universal-instantiation
composition, a changed-description null, and thirteen adjacent refusals.
**All 2,507 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1346→1346 | 792→794 (+2) | 25/20→27/21 (+2/+1) | 6 / 4 | 611→611 |
| dev-holdout | 1323→1325 (+2) | 785→789 (+4) | 22/15→22/15 | 9 / 5 | 572→572 |

Across all gold kinds the reader appears in thirteen rows / four stories on
train and thirteen rows / five stories on holdout. Two fixed Dickinson rows
are excluded from movement accounting. The exact before/after premise audit
shows the summer-Olympic-games story is the sole new all-premises-read stack:
its two actionable queries become stack-ready. Documentary membership adds
two holdout fact-bearing premises; the MoMA story supplies the other two
holdout fully-read gains. Other occurrences were already fully read.

Cumulative recorded-frame state is 794/1647 and 789/1607 fully read, 611/572
truth-scope vetoes, 21/15 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-eight classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train stack readiness is now one
story short at 21/22; fully-read and veto thresholds still bind, so a final
stack buyer does not by itself schedule look #6.

---

# Session 51 (2026-07-22): Phase B reader 37 — past definite-PP existentials; +2 train fully read, +1 stack-ready story

One reader serves **“There was a/an CLS PREPOSITION the DESCRIPTION.”** The
past existential, indefinite class, definite article, one condensed noun
object, and terminal period bind the complete construction. It emits an
`Existential(CLS, PREPOSITION+qualified DESCRIPTION)` without inventing a
witness. Coordination, sign, counts, named/indefinite PP objects, further
PPs, relative tails, other agreement, and missing boundaries stay unread.

Sixteen synthetic pins cover exact qualified emission, existing existential
composition, a changed-description null, and thirteen adjacent refusals.
**All 2,491 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1344→1346 (+2) | 790→792 (+2) | 23/19→25/20 (+2/+1) | 2 / 1 | 611→611 |
| dev-holdout | 1323→1323 | 785→785 | 22/15→22/15 | 0 / 0 | 572→572 |

Across all gold kinds the reader appears in three train rows / one story and
no holdout rows. The third row is the fixed event/time exclusion; the two
actionable verdict rows gain the final premise reader and become stack-ready.
Their already-correct outcomes remain unchanged. Hazards are neutral.

The regenerated frontier first exposed **“Robert Lewandowski left Bayern
Munchen.”** The ground-event reader already exists; the blocker is lexical.
Admitting `left → leave` in shared core bought that train story but rerouted
many arithmetic remainder asks (`have left`) and failed the full suite, so the
experiment was reverted and remains banked. The counted-existential closer
from Session 50 remains banked for its separate key-rendering problem.

Cumulative recorded-frame state is 792/1647 and 785/1607 fully read, 611/572
truth-scope vetoes, 20/15 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-seven classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train stack readiness remains the
binding story threshold at 20/22; require a whole-construction buyer rather
than global lexical ambiguity or partial counted-existential consumption.

---

# Session 50 (2026-07-22): Phase B reader 36 — four-name asyndetic copular lists; +2 holdout fully read, +1 stack-ready story

One reader serves **“A, B, C, D are P.”** It is deliberately separate from
reader 34's exactly-three conjunction/Oxford-comma construction: three comma
boundaries and no conjunction prove the four-name asyndetic list. Plural
agreement singular-folds the shared predicate, and one positive `Atom` is
emitted for each name. The inherited article refusal excludes collective
predicates such as “are a team.”

Nineteen synthetic pins cover exact emission, existing copular-ask
composition, an unlisted-name null, and sixteen adjacent refusals. Shorter or
longer lists, explicit conjunction/disjunction, missing punctuation,
non-name members, singular agreement, collectives, sign, leading material,
and apposition remain unread.

**All 2,475 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1344→1344 | 790→790 | 23/19→23/19 | 0 / 0 | 611→611 |
| dev-holdout | 1321→1323 (+2) | 783→785 (+2) | 21/14→22/15 (+1/+1) | 2 / 1 | 572→572 |

Across all gold kinds the reader appears in three holdout rows / one story
and no train rows. It records four exact `district in the city of Guilin`
atoms, including Xiufeng's. One represented query now has a complete,
overlapping premise stack, but the stricter `district in Guilin` conclusion
key remains unmatched, so the outcome safely stays undetermined. All hazards
remain neutral.

The post-reader survey rejected the newly exposed train closer **“One
six-way tie was on the leaderboard, and one person in the six-way tie was
from Belgium.”** It is two coordinated counted existentials, but current
condensation splits each hyphenated counted NP across units. Representing the
class without retaining its cardinal as predicate text needs new
count-stripping key machinery; consuming the conjunction without that
semantics would be partial reading. The construction remains banked.

Cumulative recorded-frame state is 790/1647 and 785/1607 fully read, 611/572
truth-scope vetoes, 19/15 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-six classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train stack readiness remains the
binding story threshold; counted-existential coordination needs an
independently bought key representation before reconsideration.

---

# Session 49 (2026-07-22): Phase B reader 35 — reversed definite role memberships; +1/+2 fully read

One construction serves **“The ROLE of OWNER is/was MEMBER.”** The definite
description identifies a named member of one exact owner-qualified role, so
the paired tense readers emit positive `Atom(MEMBER, ROLE+of+OWNER)`. They do
not assert identity, aliasing, or a bare-role property. Separate `is` and
`was` rules preserve the copular boundary without admitting arbitrary verbs.

Twenty synthetic pins cover both tenses, exact copular-ask composition, a
changed-owner null, and sixteen adjacent refusals. Indefinite or missing
determiners, missing/extra role structure, other copulas, sign,
common/pronominal members, coordination, modality, relatives, apposition,
and trailing material remain whole-unread.

**All 2,456 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1344→1344 | 789→790 (+1) | 23/19→23/19 | 1 / 1 | 611→611 |
| dev-holdout | 1321→1321 | 781→783 (+2) | 21/14→21/14 | 2 / 1 | 572→572 |

Across all gold kinds the reader appears in two train rows / one story and
three holdout rows / one story. It records `winner of 1992 du Maurier
Classic(Steinhauer)` and `lead singer of Imagine Dragons(Dan)`. The old fold
already made both premises fact-bearing; each story still has a separate
blocked premise, so stack readiness and outcomes remain unchanged. The train
fragment guard explicitly keeps the exact negated echo declined while its
coordinated sibling premise is unread. All hazards remain neutral.

The post-reader survey rejected the tempting train closer **“Deborah Wallace
co-produced Gasland.”** Tokenization currently drops the hyphen, leaving
unknown `co` before `produced`; preserving that boundary could support a
general prefixed-verb reader, but the resulting `co-produce Gasland` key has
no existing conclusion or inference join in the story. It is therefore not a
bought infrastructure increment and remains banked.

Cumulative recorded-frame state is 790/1647 and 783/1607 fully read, 611/572
truth-scope vetoes, 19/14 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-five classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train stack readiness remains the
binding story threshold; require a real key join before revisiting prefixed
verbs or other infrastructure.

---

# Session 48 (2026-07-22): Phase B reader 34 — three-name distributive copular subjects; +2/+2 fully read and −2/−2 vetoes

One reader serves **“A, B and C are P”** and its Oxford-comma sibling. It is
the exactly-three extension of the existing two-name distributive rule:
plural agreement singular-folds the shared predicate, and the reader emits
one positive `Atom` for each named subject. The inherited indefinite-article
refusal keeps collective predicates such as “are a team” unread; sign,
disjunction, non-name members, and shorter or longer lists also refuse.

Twenty synthetic pins cover ordinary and Oxford punctuation, exact copular
composition, an unlisted-name null, and sixteen adjacent refusals.

**All 2,436 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1342→1344 (+2) | 787→789 (+2) | 23/19→23/19 | 2 / 1 | 613→611 (−2) |
| dev-holdout | 1319→1321 (+2) | 779→781 (+2) | 21/14→21/14 | 2 / 1 | 574→572 (−2) |

Across all gold kinds the reader appears in three rows / one story on each
split. Train distributes `play by Deborah Wallace` over three named works;
holdout distributes `located in the South Shetland Islands` over three named
islands. Each story still has one unrelated blocked premise, so neither is
stack-ready yet. All hazards remain neutral.

The mandatory banked-zero recheck prototyped the general sibling **“If
someone is P, then they V Q.”** Nineteen synthetic tests passed, but it
matched zero DEV rows: the only apparent buyer uses ambiguous `work`, which
cannot satisfy the required event-verb gate. The prototype was removed and
stays banked; weakening that gate would erase the grammatical evidence.

Cumulative recorded-frame state is 789/1647 and 781/1607 fully read, 611/572
truth-scope vetoes, 19/14 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-four classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train stack readiness remains the
binding story threshold; the `someone … they work` bank needs independent
sense-resolution evidence before it can be reconsidered.

---

# Session 47 (2026-07-22): Phase B reader 33 — reversed named memberships; +2 holdout fully read, +1 stack-ready story

One reader serves **“One of the CLSs of OWNER was MEMBER.”** The first `of`
is the partitive quantifier skeleton; the second remains inside the exact
owned-class key. Because the sentence identifies the witness by name, the
reader emits positive `Atom(MEMBER, singular(CLS)+of+OWNER)` rather than an
anonymous existential. Typed class, owner, and member boundaries plus a
claimed terminal period keep larger or differently scoped constructions
whole-unread.

Nineteen synthetic pins cover exact emission, exact copular-ask composition,
a changed-owner null, and sixteen adjacent refusals. Counts, missing
articles/owners, extra PPs, other copulas, negation, nominal or pronominal
members, coordination, adjunct tails, apposition, modality, relatives, and
larger subjects all remain unread.

**All 2,416 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1342→1342 | 787→787 | 23/19→23/19 | 0 / 0 | 613→613 |
| dev-holdout | 1319→1319 | 777→779 (+2) | 20/13→21/14 (+1/+1) | 3 / 1 | 574→574 |

Across all gold kinds the rule appears in five holdout rows / one story and
no train rows. It records `Herodicus` as a `tutor of Hippocrates`; the story's
represented conclusion becomes stack-ready without a new substitution rule
or an outcome change. All hazards remain neutral.

Cumulative recorded-frame state is 787/1647 and 779/1607 fully read, 613/574
truth-scope vetoes, 19/14 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-three classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train stack readiness remains the
binding story threshold; continue requiring a general grammar class and an
existing exact-key composition path.

---

# Session 46 (2026-07-21): Phase B reader 32 — PP-restricted “None of” verbal universals; +2 train fully read, +1 stack-ready story

One reader serves **“None of the CLSs PREPOSITION R V the P.”** The
bare-plural head and bare-form event verb prove generic agreement; the single
PP remains inside the exact restrictor key. Both definite articles and a
terminal period are claimed explicitly. The reader emits negative
`Quantified(CLS+PP, V+P)` and reuses universal instantiation unchanged.

Nineteen synthetic pins cover exact emission, negative-event instantiation,
a changed-restriction null, and sixteen adjacent refusals. Singular or
articleless restrictors, missing/multiple PPs, relative clauses, sign,
modality, indefinite or counted objects, coordination, perfect verbs, and
larger object tails all remain whole-unread.

**All 2,397 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1342→1342 | 785→787 (+2) | 22/18→23/19 (+1/+1) | 2 / 1 | 613→613 |
| dev-holdout | 1319→1319 | 777→777 | 20/13→20/13 | 0 / 0 | 574→574 |

The buyer records `kid in our family → not love opera`; Billy’s exact ground
membership can instantiate that event denial. The currently represented
student/scientist conclusion does not use it, so the story becomes stack-ready
without an outcome change or unrelated inference bridge. All hazards remain
neutral.

Cumulative recorded-frame state is 787/1647 and 777/1607 fully read, 613/574
truth-scope vetoes, 19/13 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-two classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train stack readiness remains the
binding story threshold; continue preferring structurally explicit readers
over lexical, coreference, or definite-kind guesses.

---

# Session 45 (2026-07-21): Phase B reader 31 — direct passive named-agent premises; +2 train fully read, +1 stack-ready story

One reader serves **“The PATIENT is V-ed by NAME.”** The passive surface emits
the existing active-role `VerbalRelation(NAME, V, PATIENT)`. A definite
article and terminal period claim the whole construction; a bounded subject
span preserves multi-unit product names even when one component is not
lexically typed. A new opt-in `past_participle` matcher requires `-ed`/`-en`
morphology plus a registered lemma change, so finite, bare, and self-lemmed
verbs fail closed instead of masquerading as passive voice.

Twenty synthetic pins cover exact role reversal, composition through the
existing passive-agent membership bridge, changed-patient and missing-agent
nulls, and sixteen adjacent refusals. Those refusals keep indefinite subjects,
other copulas, finite/bare verbs, negation, progressives, coordination,
non-`by` PPs, common/indefinite agents, counted subjects, and larger tails
whole-unread.

**All 2,378 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1342→1342 | 783→785 (+2) | 21/17→22/18 (+1/+1) | 3 / 1 | 613→613 |
| dev-holdout | 1319→1319 | 777→777 | 20/13→20/13 | 0 / 0 | 574→574 |

The buyer records `produce(Chevrolet, Lumina APV)`. The story’s other exact
facts already make one conclusion answerable; the newly completed passive
premise makes one additional represented conclusion stack-ready but does not
change its verdict. No relation-to-class or named-object substitution was
added, and all hazards remain neutral.

Cumulative recorded-frame state is 785/1647 and 777/1607 fully read, 613/574
truth-scope vetoes, 18/13 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty-one classes are served. No TEST look was spent.

**Next:** regenerate the exact frontier. Train readiness remains binding;
prefer a construction with a cross-split buyer and an existing exact-key
composition path over lexical, reference-resolution, or substitution guesses.

---

# Session 44 (2026-07-21): Phase B reader 30 — named-PP existential premises; +3 holdout fully read, +1 stack-ready story

One reader serves **“There is a/an CLS PREPOSITION NAME.”** `there` contributes
existence but never becomes an entity. Typed noun, preposition, and name slots
give the indefinite NP and PP exact boundaries; a claimed terminal period
enforces sentence exhaustion. The reader emits `Existential(cls, prep+name)`.
Plural copulas, other determiners, signed/coordinated classes, common or
counted objects, relative clauses, and passive tails refuse.

Nineteen synthetic pins cover exact emission without a witness, existential
echo composition, a different-object null, and sixteen adjacent refusals. The
refusal suite caught the matcher’s single-slot prefix behavior and bought the
explicit endpoint before measurement. The DEV survey finds three holdout
verdict rows in one story and no train rows; the other three `There is a/an …`
surfaces are structurally larger and remain unread.

**All 2,358 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1342→1342 | 783→783 | 21/17→21/17 | 0 / 0 | 613→613 |
| dev-holdout | 1316→1319 (+3) | 774→777 (+3) | 18/12→20/13 (+2/+1) | 3 / 1 | 574→574 |

The buyer emits `∃ person: from India`. Existing existential consumers support
exact echoes and witness checks but no existential-through-universal chaining,
so the BRICS conclusions safely remain undetermined. No inference code or
synthetic witness was added, and every hazard is neutral.

Cumulative recorded-frame state is 783/1647 and 777/1607 fully read, 613/574
truth-scope vetoes, 17/13 stack-ready stories, collision 8/9, and quarantine
16/18. Thirty classes are served. No TEST look was spent.

**Next:** continue the beyond-one-away survey with train readiness still
binding. The remaining train candidates require explicit infrastructure;
prefer a general construction with independently proven composition.

---

# Session 43 (2026-07-21): Phase B reader 29 — participial compound verbal universals; +1 holdout fully read and stack-ready story

One reader serves **“V-ing CLSs V2 P.”** An opt-in present-participle modifier
plus a plural class head forms the exact membership key; a bare-form main verb
proves plural agreement and preserves the ground-verbal predicate shape. A
skipped definite article is blocked, as are finite/adjectival modifiers,
singular classes, state/modal/signed or coordinated consequences,
particle/perfect verbs, relatives, and counted tails.

Twenty synthetic pins cover exact emission, named instantiation, a missing-
membership null, and seventeen adjacent refusals. The refusal work exposed and
closed definite-article and adverb-sensed particle leaks. The exact survey
finds one holdout verdict row in one story, plus two text-gold copies, and no
train rows.

**All 2,339 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1342→1342 | 783→783 | 21/17→21/17 | 0 / 0 | 613→613 |
| dev-holdout | 1316→1316 | 773→774 (+1) | 17/11→18/12 (+1/+1) | 1 / 1 | 575→574 (−1) |

The buyer now records `hold company → hold several company`; the premise was
already fact-bearing through a lossy fold, so that count does not rise.
Koei Tecmo’s longer coordinated class description has no licensed exact
subclass bridge, leaving the verdict correctly undetermined. Agreement-
ambiguity diagnostics also decrease by one; no hazard increases.

Cumulative recorded-frame state is 783/1647 and 774/1607 fully read, 613/574
truth-scope vetoes, 17/12 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-nine classes are served. No TEST look was spent.

**Next:** re-survey beyond the one-away pool. The remaining train one-away
candidates require lexical, passive, definite-description, or coreference
infrastructure; do not disguise those choices as grammar-only readers.

---

# Session 42 (2026-07-21): Phase B reader 28 — inclusive indefinite-generic disjunctions; +2 train fully read, +1 stack-ready story

One reader serves **“A/An CLS is a/an L or a/an R.”** The three articles
prove a generic nominal class and two nominal branches even when a branch noun
is unknown. Bare `or` emits the existing `QuantifiedDisjunction` with
`exclusive: false`; unlike Reader 10’s overt-`either` sibling, knowing one
branch cannot refute the other. Signed, coordinated, verbal, prepositional,
articleless, either-marked, and larger disjuncts refuse.

Twenty synthetic pins cover exact inclusive emission, case-analysis
composition, the absence of exclusive elimination, a missing-membership null,
and sixteen adjacent refusals. The exact survey finds two train verdict rows
in one story, plus one text-gold copy, and no holdout rows.

**All 2,319 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1342 (+2) | 781→783 (+2) | 20/16→21/17 (+1/+1) | 2 / 1 | 615→613 (−2) |
| dev-holdout | 1316→1316 | 773/1607→773/1607 | 17/11→17/11 | 0 / 0 | 575→575 |

The buyer story now records `photographer → professional ∨ amateur` and is
fully read. Its represented Alba Roversi conclusion becomes stack-ready but
remains undetermined: replacing the named object `Roversi` with its property
`Italian surname` requires a separate relational substitution inference, not
disjunction reasoning. No inference code was added and all hazards are neutral.

Cumulative recorded-frame state is 783/1647 and 773/1607 fully read, 613/575
truth-scope vetoes, 17/11 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-eight classes are served. No TEST look was spent.

**Next:** regenerate the one-away frontier. Train stack readiness remains the
binding story threshold; keep relational substitution and lexical/coreference
work separate from premise readers.

---

# Session 41 (2026-07-21): Phase B reader 27 — free-relative verbal consequences; +1 train fully read and stack-ready story

One reader serves **“If a/an CLS V P, they V2 what SUBJECT V3 Q.”** The
second verb is internal to the free-relative object, so the reader preserves
`what SUBJECT V3 Q` inside the outer consequence key rather than asserting a
second proposition or letting a general span swallow an arbitrary clause.
Only the comma-bound skeleton is bought. Explicit-`then`, sign, modality,
coordination, auxiliaries, perfect/particle forms, and counted siblings refuse.

Nineteen synthetic pins cover exact emission, named composition, a missing-
antecedent null, and sixteen adjacent refusals. The exact survey finds one
train verdict instance in one story and no holdout instances.

**All 2,299 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs and both grouped logic
diffs are NEUTRAL. Outcomes remain train 21 correct / 1 pre-existing
poisoned-text wrong / 472 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 780→781 (+1) | 19/15→20/16 (+1/+1) | 1 / 1 | 616→615 (−1) |
| dev-holdout | 1316→1316 | 773/1607→773/1607 | 17/11→17/11 | 0 / 0 | 575→575 |

The buyer now records `play football → play what American call soccer`, but
the story’s ground fact is `Adam Buska → European football player`; no exact
membership/event bridge joins those keys. That separate inference or premise
construction remains unimplemented, so the verdict correctly stays
undetermined. No inference code was added and all hazards remain neutral.

Cumulative recorded-frame state is 781/1647 and 773/1607 fully read, 615/575
truth-scope vetoes, 16/11 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-seven classes are served. No TEST look was spent.

**Next:** regenerate the one-away frontier, continuing to prioritize exact
train stack gains. Keep the European-football membership/event bridge banked
until a general construction and composition proof exist.

---

# Session 40 (2026-07-21): Phase B reader 26 — plural positive possessive universals; +7/+4 fully read, +1 train solve

One reader serves **“All CLSs have P.”** Plural agreement licenses a singular
class key while leaving the possessed predicate echo-exact. Relative markers,
extra verbs, sign, modality, coordination, quantified objects, and merged
counted nouns refuse, preventing inner relative-clause `have` surfaces and
cardinality-bearing material from being flattened into universals.

Fifteen synthetic pins cover exact emission, named instantiation, a missing-
membership null, and twelve adjacent refusals. The reader matches 7 verdict
instances / 3 stories on train and 4 / 2 on holdout (9 / 3 and 7 / 3 when text
golds are included).

**All 2,280 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV diffs are NEUTRAL. The grouped
logic train diff safely SOLVES one item with 0 BROKE and 0 DECL→WRONG; holdout
is NEUTRAL. Outcomes become train 21 correct / 1 pre-existing poisoned-text
wrong / 472 declined and remain holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched verdict instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 773→780 (+7) | 18/14→19/15 (+1/+1) | 7 / 3 | 623→616 (−7) |
| dev-holdout | 1316→1316 | 769/1607→773/1607 (+4) | 17/11→17/11 | 4 / 2 | 579→575 (−4) |

The solve composes `horse → have hooves` with `human → not have hooves`;
existing `synth/negative-chain` derives `human → not horse` and refutes the
existential query. No inference code was added. Hazards remain neutral.

Cumulative recorded-frame state is 780/1647 and 773/1607 fully read, 616/575
truth-scope vetoes, 15/11 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-six classes are served. No TEST look was spent.

**Next:** regenerate the one-away frontier, prioritizing exact cross-split
families and the remaining train stack deficit. Avoid lexical/coreference
guesses and keep later inference consumers separate from premise readers.

---

# Session 39 (2026-07-21): Phase B reader 25 — active participial possessive universals; +6 train fully read, +1 train stack-ready story

One reader serves **“Everyone V-ing P has Q.”** The active participial clause
is a universal restrictor, so the surface emits the exact existing
`Quantified(V(P), have(Q))` implication rather than inventing a referent for
`Everyone`. A new opt-in `present_participle` matcher requires an `-ing`
surface whose registered lemma differs; finite verbs, `-ing`-final bare
lemmas, passive relatives, particles/perfects, sign, modality, coordination,
counted material, and non-possessive consequences refuse.

Fifteen synthetic pins cover exact emission, named instantiation, a null
antecedent, and twelve morphology/scope/adjacency refusals. The exact rule
survey finds six train instances in one grouped story and zero holdout
instances.

**All 2,265 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Verified grouped
outcomes remain train 20 correct / 1 pre-existing poisoned-text wrong / 473
declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 767→773 (+6) | 17/13→18/14 (+1/+1) | 6 / 1 | 623→623 |
| dev-holdout | 1316→1316 | 769/1607→769/1607 | 17/11→17/11 | 0 / 0 | 579→579 |

The buyer premise already had an unrelated fallback fact, explaining the
neutral fact-bearing count. It is now wholly read and its one represented
student conclusion is stack-ready, but remains undetermined pending a
separate deeper disjunctive case-propagation increment. Hazards remain neutral.

Cumulative recorded-frame state is 773/1647 and 769/1607 fully read, 623/579
truth-scope vetoes, 14/11 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-five classes are served. No TEST look was spent.

**Next:** regenerate the one-away frontier after reader 25, prioritizing
cross-split fully-read gains and additional train stack stories. Keep the
buyer’s deeper case inference separate from the premise construction.

---

# Session 38 (2026-07-21): Phase B reader 24 — grammar-proven fused premise/question boundaries; +0/+5 fully read, +1 holdout stack-ready story

One document-reader construction recovers a missing terminal boundary in
**“PREMISE Is it true that …?”** without hardcoding that wrapper. A capitalized
token merely proposes a split: the left fragment must be consumed end-to-end
by one fact-emitting read rule, and the right fragment end-to-end by one ask
rule. Existing leading/trailing conditional splitters run first, and an
already complete question takes a fast path. Partial/floating matches and
unknown left fragments remain fused and decline.

Eight synthetic pins cover exact splitting, positive and negative end-to-end
verdicts, preservation of a disjunction without asserting either branch, and
four refusals/compatibility cases. The exact-boundary survey finds no matches
in the eight standard DEV slices or FOLIO train; all five holdout verdict
instances in the tennis story match.

**All 2,250 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes remain
train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined and
holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 767→767 | 17/13→17/13 | 0 / 0 | 623→623 |
| dev-holdout | 1311→1316 (+5) | 764/1602→769/1607 (+5/+5 denominator) | 12/10→17/11 (+5/+1) | 5 / 1 | 579→579 |

The buyer's final disjunctive premise had been fused into each question and
therefore omitted from premise accounting. Reader 24 restores it as a fully
read `Disjunction`, exposes the existing asks, and makes all five verdict
items stack-ready. The current inference/consumer layer still cannot decide
their negative, neither/nor, and conditional conclusions, so this is readiness
rather than answer conversion. Hazards remain neutral.

Cumulative recorded-frame state is 767/1647 and 769/1607 fully read, 623/579
truth-scope vetoes, 13/11 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-four construction classes are served. The holdout stack-story
threshold is exceeded; the fully-read, veto, and train stack thresholds remain
conjunctively unmet. No TEST look was spent.

**Next:** re-survey premise readers for cross-split fully-read and train-stack
movement. Keep the tennis conclusion consumers banked as distinct inference
classes; the boundary reader has already isolated their exact remaining gaps.

---

# Session 37 (2026-07-21): Phase B reader 23 — second-person generic conditionals; +0/+5 fully read

One reader serves **“If you are a P, then you are a Q.”** Repeated generic
`you` supplies a single universally bound variable rather than a discourse
referent, so the surface emits the existing positive `Quantified(P, Q)` fact.
Both indefinite articles and the comma/`then` boundary are required; signed,
coordinated, modal, verbal, counted, mixed-person, and comma-less siblings
remain whole-unread.

Seventeen synthetic pins cover exact emission, named instantiation, universal
chaining, a missing-antecedent null, and thirteen adjacent/larger refusals.
The reader matches one holdout story and no train story. It makes the exact
chain `Grand Slam champion → World Tour player → professional tennis player`
available, while negative chaining also propagates the story's stated
disjointness.

**All 2,242 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes remain
train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined and
holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 767→767 | 17/13→17/13 | 0 / 0 | 623→623 |
| dev-holdout | 1306→1311 (+5) | 759→764 (+5) | 12/10→12/10 | 5 / 1 | 584→579 (−5) |

All premises in the buyer story are now fully read across its five verdict
items. Stack readiness does not rise because the story's conclusion surfaces
still lack ask readers; this increment therefore prepares an exact inference
stack without claiming answer coverage. Collision, quarantine, agreement,
ambiguity, and clause-split hazards remain neutral.

Cumulative recorded-frame state is 767/1647 and 764/1602 fully read, 623/579
truth-scope vetoes, 13/10 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-three construction classes are served. The holdout stack-story
threshold remains met; the fully-read, veto, and train stack thresholds remain
conjunctively unmet. No TEST look was spent.

**Next:** survey the newly premise-complete tennis story's conclusion surfaces
alongside other cross-split ask gaps, but require any ask reader to prove an
exact fact-key join and safe polarity behavior. Continue preferring premise
readers when they offer broader fully-read or stack-ready movement.

---

# Session 36 (2026-07-21): Phase B reader 22 — implicit-restrictor property universals; +0/+2 fully read, +1 holdout stack-ready story

One construction class serves the dual surfaces **“Anything P is Q”** and
**“No one P is Q.”** The implicit subjects supply the quantified variable;
the property after them is the restrictor, and the final copular predicate is
the positive or negative consequence. Both emit existing `Quantified` facts.
The narrow negative sibling also emits the semantically exact `P → not Q`
key alongside the older generic fallback's over-literal `one P → not Q`, so
existing behavior is preserved while universal chaining gains the correct
join.

Nineteen synthetic pins cover both exact emissions, named instantiation, the
positive-to-negative universal chain, a missing-antecedent null, and fourteen
refusals for adjacent or larger constructions. A first positive-only probe
was rejected: it improved raw reading but could not close the target chain
because the negative premise still carried the literal `one` in its key.

**All 2,225 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV snapshot diffs and both
FOLIO-with-logic grouped diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes
remain train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined
and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 767→767 | 17/13→17/13 | 0 / 0 | 623→623 |
| dev-holdout | 1304→1306 (+2) | 757→759 (+2) | 11/9→12/10 (+1/+1) | 2 / 1 | 584→584 |

The buyer story states `lazy → unproductive`, `unproductive → not energetic`,
and `sloth → lazy`, plus an existential sloth witness. The paired reader makes
all five premises fully read and the item stack-ready; saturation derives the
exact universal chain `lazy → not energetic`. The conjunctive conclusion
consumer still declines, so this is readiness movement rather than an answer
conversion. Hazards remain neutral.

Cumulative recorded-frame state is 767/1647 and 759/1602 fully read, 623/584
truth-scope vetoes, 13/10 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-two construction classes are served. The holdout stack-story
threshold is met exactly, but the fully-read, veto, and train stack thresholds
remain conjunctively unmet. No TEST look was spent.

**Next:** keep prioritizing readers that improve stack readiness, especially
cross-split families, while pricing the larger fully-read and truth-veto gaps.
The newly exposed conjunctive conclusion consumer is a separate frontier and
must earn its own general construction-class increment.

---

# Session 35 (2026-07-21): Phase B reader 21 — repeated both-or-neither equivalence; +0/+2 fully read, +2 holdout solves

One reader serves **“NAME is either both A and B or neither A nor B.”** The
surface states `(A ∧ B) ∨ (¬A ∧ ¬B)`, exactly the existing ground
`Equivalence(A, B)` contract. A new opt-in `same_phrase` where-predicate
compares canonical slot values—including spans—so the reader only fires when
the negative branch repeats both positive predicates in the same order.
Mismatched and swapped repeats remain whole-unread.

Eleven synthetic pins cover exact emission, positive and negative propagation,
composition through disjointness plus reductio, and seven refusals for
ordinary disjunction/conjunction, mismatched or swapped repeats, signed and
trailing larger constructions, and indefinite subjects.

**All 2,206 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV snapshot diffs are NEUTRAL.
The FOLIO-with-logic train diff is neutral and holdout safely SOLVES two
items, with 0 BROKE and 0 DECL→WRONG. Outcomes become train 19 correct / 1
pre-existing poisoned-text wrong / 474 declined and holdout 4 / 0 / 421.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 767→767 | 17/13→17/13 | 0 / 0 | 623→623 |
| dev-holdout | 1304→1304 | 755→757 (+2) | 9/8→11/9 (+2/+1) | 2 / 1 | 586→584 (−2) |

The buyer story already states that humans are animals, flowers are plants,
and no animals are plants. Equating a named subject's human and flower
predicates makes their positive branch inconsistent; the existing reductio
engine derives `not human`, and modus tollens through `pupil → human` derives
`not pupil`. The positive and negative pupil questions therefore both move
to their correct verdicts. Hazards remain neutral.

Cumulative recorded-frame state is 767/1647 and 757/1602 fully read, 623/584
truth-scope vetoes, 13/9 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty-one construction classes are served. The holdout stack-story
threshold is now one story away, but all Phase C thresholds remain conjunctive
(852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** continue the one-reader-away holdout survey, but do not optimize only
for the final holdout stack story: the fully-read and veto thresholds remain
the larger gaps. Prefer a cross-split reader when its inference keys are exact.

---

# Session 34 (2026-07-21): Phase B reader 20 — reduced-relative people universals; +0/+1 fully read, +1 holdout solve

One reader serves **“People V P are Q”** where the non-state verb phrase is a
reduced relative and `Q` is a copular predicate. As in the established
`people` conditional family, the human subject supplies the unrestricted
variable; the exact reduced-relative key becomes the positive `Quantified`
antecedent. A one-content-unit capitalized fallback-name span now follows the
same `.singular` morphology as a one-unit slot, so a plural-agreeing predicate
such as `Americans` joins the singular `American` conclusion without a
word-specific kernel table. Multi-unit name spans remain untouched.

Eleven synthetic pins cover exact key emission, named-witness composition, a
missing-restrictor null, a multiword-name exactness guard, and seven refusals for signed antecedents and
consequences, coordination, counts, overt relatives, verbal consequences,
and definite subjects. The first single-token draft was rejected because it
partially accepted a coordinated consequence; the shipped span consumes the
whole predicate and blocks that larger construction.

**All 2,195 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV snapshot diffs are NEUTRAL.
The FOLIO-with-logic train diff is neutral and holdout safely SOLVES one item,
with 0 BROKE and 0 DECL→WRONG. Outcomes become train 19 correct / 1
pre-existing poisoned-text wrong / 474 declined and holdout 2 / 0 / 423.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 767→767 | 17/13→17/13 | 0 / 0 | 623→623 |
| dev-holdout | 1304→1304 | 754→755 (+1) | 8/7→9/8 (+1/+1) | 1 / 1 | 587→586 (−1) |

The buyer story already represented a named birth fact and asks whether that
person is American; this reader closes its sole missing premise and the
existing universal-instantiation synth derives the gold conclusion. Collision,
quarantine, agreement, ambiguity, and clause-split hazards are neutral.

Cumulative recorded-frame state is 767/1647 and 755/1602 fully read, 623/586
truth-scope vetoes, 13/8 stack-ready stories, collision 8/9, and quarantine
16/18. Twenty construction classes are served; every Phase C threshold still
binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** keep selecting holdout stories that are one exact reader away from
stack-ready. Re-price the remaining compound generic, existential, and
two-blocker conditional candidates before broad train-only readers.

---

# Session 33 (2026-07-21): Phase B reader 19 — indefinite-generic verbal conditionals; +2/+0 fully read

One pack-only increment serves **“If a/an CLS V P, [then] they V2 Q.”**
Paired explicit-`then` and comma-only readers encode the article-licensed
singular generic with a third-person-singular antecedent event and a plural
bare-form consequence event. Both flat keys echo named ground-verbal facts,
so positive `Quantified` instantiation composes without new schema or kernel
behavior.

Fifteen synthetic pins cover both skeletons, exact key emission, named-event
instantiation, a missing-antecedent null, and eleven refusals for other
subjects, signed/modal/state/copular consequences, adverbs, coordination,
particles, and counts. The comma-only form is separately claimed so an
explicit `then` cannot be swallowed into the antecedent span.

**All 2,184 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes remain
train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined and
holdout 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1340→1340 | 765→767 (+2) | 17/13→17/13 | 2 / 1 | 625→623 (−2) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

The sole buyer story states that a person who pays their taxes contributes to
the country, emitting `pay their tax → contribute to country` across two train
item instances. The holdout-looking `gains knowledge … become smarter` form
does not match because its event heads and predicate are unknown in the
current lexicon; vocabulary expansion remains a separate enabler. The train
items' coordinated asks stay declined, so outcomes and stack readiness are
unchanged. Collision, quarantine, agreement, ambiguity, and clause-split
hazards are neutral.

Cumulative recorded-frame state is 767/1647 and 754/1602 fully read, 623/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Nineteen construction classes are served; every Phase C threshold
still binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** continue pricing exact coordination and conditional siblings. Bank
negative verbal consequences and the unknown-vocabulary `gains knowledge`
surface until their lexical or composition enablers are independently bought;
passive relations still require direction-aware keys.

---

# Session 32 (2026-07-21): Phase B reader 18 — people copular-to-verbal conditionals; +2/+0 fully read

One pack-only increment serves **“If people are P, then they V Q.”** The
plural-agreeing copular antecedent singular-folds to the same key as a named
ground atom, while the bare, single-token non-state consequence head renders
the same event key as named ground-verbal facts and questions. It emits an
existing positive `Quantified` fact, so the existing universal-instantiation
synth supplies the whole inference path.

Fifteen synthetic pins cover exact emission, direct instantiation, a missing-
antecedent null, preservation of a coordinated antecedent as one exact opaque
key, and eleven refusals for other subjects, restricted subjects, negative
antecedents, copular/signed/modal/adverbial/coordinated/particle and counted
consequences. A preceding unrestricted verbal-to-verbal prototype passed its
synthetic stack but matched zero DEV premises because its apparent buyers had
unknown verb heads or larger structures; it was removed under the
enabler-must-be-bought rule.

**All 2,169 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes remain
train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined and
holdout 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1340 (+2) | 763→765 (+2) | 17/13→17/13 | 2 / 1 | 627→625 (−2) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

The sole buyer story states that people fascinated by Renaissance history
attend Renaissance fairs, emitting the exact universal `fascinated by history
of renaissance and past era → attend renaissance fairs regularly` across two
item instances. Other story gaps keep both items from all-premises-read or
stack-ready status. Train agreement ambiguities improve by two; collision,
quarantine, other ambiguity, and clause-split hazards do not increase.

Cumulative recorded-frame state is 765/1647 and 754/1602 fully read, 625/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Eighteen construction classes are served; every Phase C threshold
still binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** continue pricing exact coordination and conditional siblings. Keep
the unrestricted people verbal-to-verbal form banked until recognized verb
heads or a larger exact construction buy it; passive relations still require
direction-aware keys.

---

# Session 31 (2026-07-21): Phase B reader 17 — positive possessive universals; +2/+0 fully read

One pack-only increment serves **“Every CLS has P.”** State syntax remains
outside the event-oriented `nonstate_verb` family; the dedicated rule
canonicalizes singular-agreeing `has P` to the same `have P` key used by
negative possessive universals and mixed possession disjunctions. It emits an
existing positive `Quantified` fact, so universal chaining and named
instantiation work without new schema or kernel behavior.

Seventeen synthetic pins cover exact emission, direct instantiation, subclass
chaining, a missing-membership null, and thirteen refusals for plural/all
agreement, non-possession, scoped `no`/`either`, coordination, do-support,
modals, verbal/perfect predicates, counts, relatives, compound classes, and
non-universal subjects.

**All 2,154 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes remain
train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined and
holdout 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 761→763 (+2) | 17/13→17/13 | 2 / 1 | 629→627 (−2) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

The sole buyer story states `Every teacher has students`, emitting the exact
universal `teacher → have student` across two item instances. Remaining
question coordination keeps both items from all-premises-read or stack-ready
status. Collision, quarantine, agreement, ambiguity, and clause-split hazards
remain unchanged.

Cumulative recorded-frame state is 763/1647 and 754/1602 fully read, 627/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Seventeen construction classes are served; every Phase C threshold
still binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** keep the holdout-only intransitive universal banked until a matching
ground/ask stack exists; continue pricing exact coordination and conditional
families before relation-dependent passive/relative shapes.

---

# Session 30 (2026-07-21): Phase B reader 16 — named possession/event disjunctions; +4/+0 fully read

One pack-only increment serves **“NAME has P or V Q.”** Bare `or` carries the
campaign's measured inclusive reading. The possession branch canonicalizes
singular-agreeing `has P` to the existing `have P` atom key, while the event
branch lemma-renders `V Q` exactly like named ground-verbal facts. The reader
therefore emits an existing ground `Disjunction`; disjunctive syllogism works
in either direction without new schema or inference code.

Nineteen synthetic pins cover exact emission, elimination from a negative
event branch, elimination from a negative possessive universal instance, a
disjunction-only null, inclusive non-elimination, and fourteen refusals.
Falsification specifically added `quantifier` and `either_marker` to the
possession span after `has either P` and `has no P` initially leaked through.
Other refusals cover copular/either-first forms, conjunction, do-support,
modals, multi-verb/particle events, counted possession, larger coordination,
three-way disjunction, and non-name subjects.

**All 2,137 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes remain
train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined and
holdout 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 757→761 (+4) | 17/13→17/13 | 4 / 1 | 633→629 (−4) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

The sole buyer story states `James has a car or works at Meta`, emitting the
exact inclusive fact `james: have car OR work at meta` across four item
instances. Other gaps keep every item from all-premises-read or stack-ready
status. Collision, quarantine, agreement, ambiguity, and clause-split hazards
remain unchanged.

Cumulative recorded-frame state is 761/1647 and 754/1602 fully read, 629/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Sixteen construction classes are served; every Phase C threshold still
binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** continue with positive possessive and intransitive universals as
separate candidates; passive/relative shapes remain gated on relation-aware
keys or an existing consumer join.

---

# Session 29 (2026-07-21): Phase B reader 15 — future-negative indefinite generics; +4/+0 fully read

One pack-only increment serves **“A/An CLS will not V P.”** The consumed
indefinite article marks a singular generic class; literal `will` is exact
tense scaffolding; explicit `not` owns polarity. The bare-form, single-token
non-event verb and predicate render exactly like ground-verbal facts and
questions, so the reader emits an existing negative `Quantified` fact and
reuses universal chaining and named instantiation.

Seventeen synthetic pins cover the exact fact, direct instantiation/refutation,
subclass chaining, a missing-membership null, and thirteen refusals spanning
other quantifiers/subjects, do-support, conditional `would`, missing/alternate
negation, copular, multi-verb, particle, coordinated, and counted forms.

**All 2,118 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV and both FOLIO-with-logic
grouped snapshot diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes remain
train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined and
holdout 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 753→757 (+4) | 17/13→17/13 | 4 / 1 | 637→633 (−4) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

The sole buyer story states that a person with a high income will not take a
bus to their destination. The exact emitted key is `person with high income
→ not take bus to meta destination`; four item instances share the story.
Other gaps keep every item from all-premises-read or stack-ready status.
Collision, quarantine, agreement, ambiguity, and clause-split hazards remain
unchanged.

Cumulative recorded-frame state is 757/1647 and 754/1602 fully read, 633/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Fifteen construction classes are served; every Phase C threshold still
binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** return to the single-veto survey. Positive possessive universals,
intransitive universals, coordination, and passive/relative families remain
separate classes; relation-dependent shapes stay banked.

---

# Session 28 (2026-07-21): Reader 14 precision correction — literal `will`, no auxiliary bycatch

Reader 15 falsification exposed an overbroad gate in reader 14 before the new
class landed. The DSL's `future_modal` slot type deliberately accepts ordinary
auxiliaries as well as `will`/`would`, because factual question readers reuse
it for do-support. In a premise rule that meant **“Students do either V P or
V2 Q”** could emit the same future-event disjunction as the intended
**“Students will either …”** construction.

The independently revertible correction replaces that slot with literal
`will`, the exact grammatical skeleton named by the reader. A new synthetic
refusal pin covers do-support. The intended buyer remains unchanged: the same
four train instances in one story move fully-read, and the same exact
`person → take bus XOR drive to meta destination` fact is emitted.

**All 2,101 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV snapshot diffs and both
FOLIO-with-logic grouped diffs are NEUTRAL against reader 14 (0 BROKE, 0
DECL→WRONG). Coverage, outcomes, and every recorded hazard are unchanged. No
TEST look was spent, and the reader count remains 14.

**Next:** resume the separately removed `A/An CLS will not V P` reader 15
prototype using literal `will`, then remeasure its exact composition and DEV
movement.

---

# Session 27 (2026-07-21): Phase B reader 14 — future-event disjunctions; +4/+0 fully read

One pack-only increment serves **“CLSs will either V P or V2 Q”** when both
branches begin with bare-form, single-token non-event verbs. The plural class
folds to its singular membership key; `will` contributes tense but no
predicate material; each `V P` branch renders exactly like an existing ground
verbal atom. Overt `either` emits an exclusive `QuantifiedDisjunction`, so the
existing instantiation, disjunctive-syllogism, and XOR-elimination synths
compose without new schema or kernel behavior.

Seventeen synthetic pins cover the exact fact, negative-left disjunctive
syllogism, positive-left exclusive elimination, missing-class and
disjunction-only nulls, plus capacity-modal, missing-`either`, singular,
definite, named, signed, coordinated, multi-verb, particle, counted,
three-way, and copular refusals. The final refusal uses Session 26's
`non_event_verb` boundary; `Students will either be happy ...` stays unread.

**All 2,100 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 twice.** All eight standard DEV snapshot diffs and both
FOLIO-with-logic grouped diffs are NEUTRAL (0 BROKE, 0 DECL→WRONG). Outcomes
remain train 19 correct / 1 pre-existing poisoned-text wrong / 474 declined
and holdout 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 749→753 (+4) | 17/13→17/13 | 4 / 1 | 641→637 (−4) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

The sole buyer story states that people will either take a bus or drive to
their destination. Its emitted key is exactly `person → take bus XOR drive
to meta destination`; four item instances share that story. Other unread
premises/questions keep it from all-premises-read or stack-ready status.
Collision, quarantine, agreement, ambiguity, and clause-split hazards remain
unchanged.

Cumulative recorded-frame state is 753/1647 and 754/1602 fully read, 637/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Fourteen construction classes are served; every numeric Phase C
threshold still binds (852/850, ≤499/460, ≥22/10). No TEST look was spent.

**Next:** continue the breadth-first survey of exact conditional,
passive/relative, and remaining coordination families; keep relation- or
coreference-dependent shapes banked until their missing stack is bought.

---

# Session 26 (2026-07-21): split event-reader exclusion from arithmetic state semantics

Reader 14's future-event disjunction prototype correctly refused finite
copulas but falsification found that bare `be` was still accepted by
`nonstate_verb`. The missing membership could not safely be added to `state`:
that category controls arithmetic holding/event folds, and the first draft
turned one GSM8K temporal offset into a confident wrong (expected 16, got 6).

The independently revertible prerequisite introduces `non_event_verb` between
`verb` and `state`. Existing quantitative state verbs inherit it; the
difg-mined forms `be`, `been`, and `being` join only the broader category.
`nonstate_verb` now excludes that structural category by fold or lemma. Three
behavior pins prove the forms cannot emit verbal universals and, critically,
are not arithmetic `state` members.

**All 2,083 tests pass; scratch lint has 0 errors and the same eight warnings;
curated is 65/65 in two fresh runs.** All eight standard DEV snapshots and
both FOLIO-with-logic grouped snapshots are NEUTRAL against reader 13: 0 BROKE
and 0 DECL→WRONG. The originally regressed GSM8K item returns to decline.
FOLIO outcomes and recorded-frame coverage/hazard metrics are unchanged, so
this borrowing earns no reader count or Phase B movement. No TEST look was
spent.

**Next:** restore the separately measured reader 14 future-event disjunction
prototype and rerun its exact/refusal/composition and full campaign gates.

---

# Session 25 (2026-07-21): Phase B reader 13 — named do-support event denials; +4/+0 fully read

One pack-only, independently revertible increment serves **“NAME does not V
P”** when `V` is a bare-form, single-token non-state verb. The explicit
negator owns polarity, while `V P` renders exactly like the existing positive
ground-verbal key. The reader emits a negative `Atom`, so the existing logic
verdict consumer can refute the corresponding positive verbal question
without a new fact, synth, schema, or kernel path.

The non-state gate remains a soundness boundary. It excludes copulas and
stative possession (`have`, `own`) rather than weakening the Stage 6 be-twin
discipline for one holdout surface. `single_word`, verb/modal/coordination
span blocks, and counted-material refusal keep particle, perfect,
multi-verb, coordinated, modal, and counted constructions whole-unread.
Thirteen synthetic pins cover the exact fact, positive-question refutation,
a different-entity null, and ten refusal surfaces.

**All 2,080 tests pass; scratch lint has 0 errors and the same eight warnings;
curated remains 65/65.** All eight standard DEV snapshot diffs are NEUTRAL
(difg, GSM8K train/holdout, ASDiv, SVAMP, MAWPS, SciBench, FOLIO), as are both
FOLIO-with-logic grouped diffs: 0 BROKE and 0 DECL→WRONG throughout. Train
remains 19 correct / 1 pre-existing poisoned-text wrong / 474 declined;
holdout remains 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 745→749 (+4) | 17/13→17/13 | 4 / 2 | 645→641 (−4) |
| dev-holdout | 1304→1304 | 754→754 | 8/7→8/7 | 0 / 0 | 587→587 |

Train serves the repeated named denials for working at a pool and catching
the sunrise. Both exact negative event atoms are consumer-compatible, but
their stories still lack other represented premises/questions, so no item
becomes all-premises-read or stack-ready. Outcomes, reasons, collision,
quarantine, agreement, ambiguous-reading, and clause-split diagnostics remain
unchanged.

The pre-reader survey also re-priced two banks. A subject-relative verbal
`All CLSs who/that V P V2 Q` prototype emitted one valid holdout
`Conditional` across five item instances but moved no fact-bearing,
fully-read, veto, stack, hazard, or outcome metric; it was removed as an
unbought enabler. The holdout ownership denial is stative and has no existing
flat-event consumer join, so it remains a separate class rather than widening
this rule.

The mandatory banked-zero recheck remains zero: no singular fold or entity
reclassification is involved, and no verbal-universal ask joins the new keys.
Cumulative recorded-frame state is 749/1647 and 754/1602 fully-read premises,
641/587 truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and
quarantine 16/18. Every numeric Phase C threshold still binds (852/850,
≤499/460, ≥22/10). No TEST look was spent.

**Next:** re-survey the remaining exact coordination and conditional families.
Passive relations, object relatives, stative ownership denials, and the
zero-movement outer-relative reader remain banked until their missing
relation/consumer stack is bought.

---

# Session 24 (2026-07-21): Phase B reader 12 — plural negative event universals; +4/+3 fully read

One pack-only, independently revertible increment serves **“No CLSs V P”**
when `V` is a bare-form, single-token non-state verb. Plural agreement
licenses `.singular` on the class key; the verb and predicate remain one exact
unfolded phrase key. The reader emits an existing negative
`Quantified(cls, pred="V P")`, so universal chaining and named instantiation
compose without new fact, synth, schema, or kernel behavior.

The first measured draft exposed an important refusal boundary: it read a
relative construction by treating `who` as part of the class and the relative
verb as the main verb, then swallowing the real unknown verb into the
predicate. The shipped class span therefore blocks all three structural
relative-marker senses (`interrogative`, `complementizer`, and `wh_which`), as
well as verbs, modals, negation, and coordination. The predicate blocks a
second verb, modals, negation, coordination, and counted material. Singular
agreement, perfects, particle verbs, and larger constructions remain unread.
Fifteen synthetic pins cover the exact fact, subclass chaining, named
instantiation, and twelve refusal surfaces.

**All 2,067 tests pass; scratch lint has 0 errors and the same eight warnings;
curated remains 65/65.** All eight standard DEV snapshot diffs are NEUTRAL
(difg, GSM8K train/holdout, ASDiv, SVAMP, MAWPS, SciBench, FOLIO), as are both
FOLIO-with-logic grouped diffs: 0 BROKE and 0 DECL→WRONG throughout. Train
remains 19 correct / 1 pre-existing poisoned-text wrong / 474 declined;
holdout remains 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1338→1338 | 741→745 (+4) | 17/13→17/13 | 4 / 1 | 649→645 (−4) |
| dev-holdout | 1304→1304 | 751→754 (+3) | 8/7→8/7 | 3 / 1 | 590→587 (−3) |

Train serves the repeated student/destination story, emitting the exact
negative verbal key after existing possessive coreference normalization.
Holdout serves the repeated Russian-Federation-official/citizenship story.
Neither story contains the missing inference/ask stack needed for a verdict,
so no item becomes all-premises-read or stack-ready. Outcomes, reasons,
collision, quarantine, agreement, ambiguous-reading, and clause-split
diagnostics remain unchanged.

The mandatory banked-zero recheck remains zero: the unknown plural fold has
none of the banked `-se`/`-ce`/`-ze` endings, `Quantified` carries no entity,
and no represented verbal-universal ask joins either key. Cumulative
recorded-frame state is 745/1647 and 754/1602 fully-read premises, 645/587
truth-scope vetoes, 13/7 stack-ready stories, collision 8/9, and quarantine
16/18. Every numeric Phase C threshold still binds (852/850, ≤499/460,
≥22/10). No TEST look was spent.

**Next:** re-survey the remaining exact conditional and passive/relative
families against the new verbal-negative join surface. Do-support, unresolved
coreference, articleless unknown-word disjunctions, and direct passive-agent
infrastructure remain banked until one exact cross-split buyer appears.

---

# Session 23 (2026-07-21): Phase B reader 11 — negative possessive universals; +1/+3 fully read

One pack-only, independently revertible increment serves **“No CLSs have P”
/ “No CLS has P”**. The plural and singular agreement frames normalize to the
same negative `Quantified(cls, pred="have P")` semantics; only the plural
class key uses `.singular`. Existing universal instantiation and chaining
provide composition, so no new fact kind, synth, schema, or kernel behavior
is required.

The class span refuses verbs and capacity/future modals, preventing relative
restrictions (`No facts that Dan knows have …`) and modal forms (`No reptiles
can have …`) from being reinterpreted as an enlarged class key. The predicate
refuses negation, coordination, and a second verb, keeping double-negative,
perfect, coordinated, and larger constructions whole-unread. Twelve
synthetic pins cover both exact agreement facts, subclass chaining, named
instantiation, and all refusal boundaries.

**All 2,052 tests pass; scratch lint has 0 errors and the same eight warnings;
curated remains 65/65.** All eight standard DEV snapshot diffs are NEUTRAL
(difg, GSM8K train/holdout, ASDiv, SVAMP, MAWPS, SciBench, FOLIO), as are both
FOLIO-with-logic grouped diffs: 0 BROKE and 0 DECL→WRONG throughout. Train
remains 19 correct / 1 pre-existing poisoned-text wrong / 474 declined;
holdout remains 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1337→1338 (+1) | 740→741 (+1) | 17/13→17/13 | 1 / 1 | 650→649 (−1) |
| dev-holdout | 1303→1304 (+1) | 748→751 (+3) | 8/7→8/7 | 3 / 2 | 593→590 (−3) |

The train buyer is `No humans have hooves`. Holdout serves `No women have
prostate cancer` and `No reptile has fur`; the latter composes with the
existing `snake → reptile` universal to derive `snake → not have fur`. Its
question item becomes all-premises-read, but `Some snake has fur` still has no
ask shape, so stack readiness and verdicts do not move. Two repeated holdout
instances were already fact-bearing through coarse readings, explaining why
fact-bearing rises by one while fully read rises by three. Outcomes, reasons,
collision, quarantine, agreement, ambiguous-reading, and clause-split
diagnostics remain unchanged.

The mandatory banked-zero recheck remains zero: the one plural fold uses
ordinary registered morphology, no fact carries an entity, and the new
verbal universal has no represented ask join. Cumulative recorded-frame state
is 741/1647 and 751/1602 fully-read premises, 649/590 truth-scope vetoes, 13/7
stack-ready stories, collision 8/9, and quarantine 16/18. No TEST look was
spent.

---

# Session 22 (2026-07-21): Phase B reader 10 — two-article indefinite disjunctions; +2/+3 fully read

One pack-only, independently revertible increment serves **“A/An CLS is
either a/an L or a/an R”** as a singular-agreeing generic exclusive
disjunction. It is the disjunctive sibling of the existing two-article
indefinite generic: the leading article marks a generic class rather than a
named witness, all keys render plain, and overt `either` carries Stage 3
exclusivity. The reader reuses `QuantifiedDisjunction`, universal
instantiation, and case analysis without adding a fact kind or synth.

The two predicate articles are a soundness boundary, not decoration. An
initial broader draft also accepted articleless disjuncts and moved +5/+7
fully-read instances, but a synthetic refusal showed that quarantined unknown
verbs could be swallowed as opaque predicate text when `span_blocks: verb`
had no registered verb sense to see. Requiring `a/an` before both branches
provides structural evidence that they are nominal. Articleless adjectival
and multiword forms remain banked, along with bare `or`, negated,
prepositional, verbal, coordinated, and three-way forms.

Fourteen synthetic pins cover the exact fact, case-analysis and XOR
composition, absent-class null, and all refusal boundaries. **All 2,040 tests
pass; scratch lint has 0 errors and the same eight warnings; curated remains
65/65.** All eight standard DEV snapshot diffs are NEUTRAL (difg, GSM8K
train/holdout, ASDiv, SVAMP, MAWPS, SciBench, FOLIO), as are both
FOLIO-with-logic grouped diffs: 0 BROKE and 0 DECL→WRONG throughout. Train
remains 19 correct / 1 pre-existing poisoned-text wrong / 474 declined;
holdout remains 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1335→1337 (+2) | 738→740 (+2) | 17/13→17/13 | 2 / 1 | 652→650 (−2) |
| dev-holdout | 1300→1303 (+3) | 745→748 (+3) | 8/7→8/7 | 3 / 1 | 596→593 (−3) |

The train buyer is the repeated function-class story; the holdout buyer is
the repeated neuroimaging-technique story. The only semantic additions are
their exact `QuantifiedDisjunction` facts: neither story contains a matching
ground class witness, so no disjunction instantiates and no item becomes
all-premises-read or stack-ready. Outcomes, reasons, collision, quarantine,
agreement, ambiguous-reading, and clause-split diagnostics remain unchanged.

The mandatory banked-zero recheck remains zero: singular folding is not used,
the fact carries no entity slot, and no verbal-universal ask joins the new
keys. Cumulative recorded-frame state is 740/1647 and 748/1602 fully-read
premises, 650/593 truth-scope vetoes, 13/7 stack-ready stories, collision 8/9,
and quarantine 16/18. No TEST look was spent.

---

# Session 21 (2026-07-21): Phase B reader 9 — restricted Everyone disjunctions; +2/+3 fully read; +1 train stack-ready story

One pack-only, independently revertible increment serves **“Everyone
RESTRICTION is [either] L or R”**. `Everyone` supplies the universally
quantified variable; the mandatory restriction is the antecedent predicate
that named ground facts can join (`at event`, for example). The reader reuses
`QuantifiedDisjunction` and the existing instantiation and case-analysis
synths. Bare `or` is inclusive and overt `either … or` exclusive under the
Stage 3 surface contract.

The exact construction refuses an empty restriction, `who` relatives,
negative disjuncts, three-way disjunctions, and verbal disjuncts. Eleven
synthetic pins cover both exact fact shapes, composition through both
branches, missing-restriction and non-decomposition nulls, and every refusal
boundary. **All 2,026 tests pass; scratch lint has 0 errors and the same eight
pre-existing warnings; curated remains 65/65.** All eight standard DEV
snapshot diffs are NEUTRAL (difg, GSM8K train/holdout, ASDiv, SVAMP, MAWPS,
SciBench, FOLIO), as are both FOLIO-with-logic grouped diffs: 0 BROKE and 0
DECL→WRONG throughout. The pre-existing poisoned text wrong remains unchanged
on train (19 correct / 1 wrong / 474 declined); holdout remains 1 / 0 / 424.

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1333→1335 (+2) | 736→738 (+2) | 16/12→17/13 (+1/+1) | 2 / 1 | 654→652 (−2) |
| dev-holdout | 1300→1300 | 742→745 (+3) | 8/7→8/7 | 3 / 2 | 599→596 (−3) |

Both train items become all-premises-read; the item with the represented
positive query also becomes stack-ready because its named restriction witness
and fact-key path coexist without a hazard. The second conclusion in that
story still lacks an ask shape. Holdout moves
three premise instances in two stories; coarse facts already existed there,
so fact-bearing stays flat while exact whole-reading consumes the previously
unread `or`. No verdict or reason changes, and collision, quarantine,
agreement, ambiguous-reading, and clause-split diagnostics remain unchanged.

The mandatory banked-zero recheck remains zero: no `_naive_singular` ending,
CamelCase entity, or verbal-universal ask joins the new keys. The preceding
survey also banked three non-readers: positive verbal `people` consequences
lack one shared train/holdout key contract; outer-quantified verbal relatives
matched 9/8 item instances but moved no reading, stack, or hazard metric; and
the apparent verbal both-or-neither sibling needs unresolved same-sentence
pronoun coreference. Cumulative recorded-frame state is 738/1647 and 745/1602
fully-read premises, 652/596 truth-scope vetoes, 13/7 stack-ready stories,
collision 8/9, and quarantine 16/18. No TEST look was spent.

---

# Session 20 (2026-07-21): Phase B reader 8 — bare-plural copular relatives; +2/+3 fully read; holdout conflicts removed

One pack-only, independently revertible increment serves **“CLSs who are P
are [not] Q”** as the class-scoped relative conditional
`∀e. CLS(e) ∧ P(e) → [¬]Q(e)`. It reuses the existing
`Conditional(cls, pred, then_pred, polarity)` fact and two-antecedent
instantiation synth. All three plural-agreeing keys render through
`.singular`, so class, relative property, and consequence meet singular
ground atoms without any kernel or schema change.

The class antecedent is semantically required: this reader does not collapse
“pets who are naughty” into the unrestricted `naughty → not-liked` implication.
The exact contract keeps definite/count-qualified and singular subjects,
negative or verbal relatives, and verbal consequences whole-unread. Ten
synthetic pins cover both polarities, exact fact shape, positive composition,
independent absence of each antecedent, and all four refusal boundaries.

**All 2,015 tests pass; scratch lint has 0 errors; curated is 65/65.** All
eight standard DEV snapshot comparisons are NEUTRAL (difg, GSM8K
train/holdout, ASDiv, SVAMP, MAWPS, SciBench, FOLIO): 0 BROKE and 0
DECL→WRONG throughout. Folio-with-logic is outcome-neutral on both splits
(train 20 correct / 1 persistent poisoned-text wrong / 473 declined; holdout
1 / 0 / 424):

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1333→1333 | 734→736 (+2) | 16/12→16/12 | 2 / 1 | 656→654 (−2) |
| dev-holdout | 1300→1300 | 739→742 (+3) | 8/7→8/7 | 3 / 1 | 599→599 |

No item becomes all-premises-read, so stack readiness does not move. The train
story changes no outcome or reason. On holdout, whole-reading the negative
pet relative removes the fallback's contradictory `pet/be` predications:
collision falls **12→9** and quarantined facts **24→18** across the actionable
pool. The three repeated item reasons improve from a fold conflict to honest
missing-logic/no-ask declines; outcome remains declined. Agreement and
ambiguous-reading diagnostics do not move, and clause split remains zero.

The banked-zero recheck remains zero: no `_naive_singular` ending, CamelCase
entity, or verbal-universal ask joins the new conditional keys. Adjacent
verbal/do-support `people` conditionals and broader passive/relative families
remain separate; re-price them against the now-cleaner join surface. Cumulative
recorded-frame state is 736/1647 and 742/1602 fully-read premises, 654/599
truth-scope vetoes, 12/7 stack-ready stories, collision 8/9, and quarantine
16/18. No TEST look was spent.

---

# Session 19 (2026-07-21): Phase B reader 7 — plural-generic people conditionals; +2/+6 fully read; all gates NEUTRAL

One pack-only, independently revertible increment serves **“If people are P,
then they are [not] Q”** as the plural-agreeing twin of the existing
`If someone is P, then they are [not] Q` reader. It emits the existing
`Quantified(cls=P, pred=Q, polarity=±)` fact with `.singular`-folded keys, so
the existing universal-instantiation synth performs composition; no kernel,
fact, schema, or synth change is needed.

This `they` does not perform the unsafe named-entity binding removed from
reader 6. The exact generic construction carries one universally quantified
subject variable from `people` into the consequent; no pronoun is resolved to
a particular person. The reader stays copular on both sides. Verbal
consequents, do-support negative consequents, negated antecedents, and the
singular `someone` construction remain separate and whole-unread. Predicate
spans stay exact phrase keys, and only explicit consequent `not` sets negative
polarity.

Synthetic coverage has nine pins: positive and negative exact fact shapes, a
passive-participial exact key, positive composition plus its null, and refusal
of verbal consequence, do-support consequence, negated antecedent, and the
singular-someone sibling. **All 2,005 tests pass; scratch lint has 0 errors;
curated is 65/65.** All eight standard DEV snapshot comparisons are NEUTRAL
(difg, GSM8K train/holdout, ASDiv, SVAMP, MAWPS, SciBench, and FOLIO): 0
BROKE and 0 DECL→WRONG throughout.

The DEV-only folio-with-logic comparison is item-level neutral in both OUTCOME
AND REASON on both splits (train 20 correct / 1 persistent poisoned-text wrong
/ 473 declined; holdout 1 / 0 / 424). The intended reading movement is:

| grouped split | fact-bearing | fully read | stack-ready items / stories | matched instances / stories | truth-scope-veto premises |
|---|---:|---:|---:|---:|---:|
| dev-train | 1333→1333 | 732→734 (+2) | 16/12→16/12 | 2 / 1 | 658→656 (−2) |
| dev-holdout | 1300→1300 | 733→739 (+6) | 8/7→8/7 | 6 / 3 | 605→599 (−6) |

No matched item becomes all-premises-read, so stack readiness does not move.
Collision and quarantine stay at 8/12 and 16/24; ambiguous-reading and
clause-split hazards do not increase. Diagnostic agreement events improve by
two on holdout because the whole conditional replaces a permissive partial
reading. The new semantic surface consists only of the four intended
quantified keys plus one existing intersective narrowing; it produces no new
ground instantiation and changes no answer reason.

The banked-zero recheck remains zero: no `_naive_singular` ending, CamelCase
entity, or represented verbal-universal ask joins the new keys. Adjacent
verbal and do-support `people` conditionals now have visible one-sided stack
potential but are distinct constructions; re-price them across both splits
before code. The next broad lever remains a narrow passive or relative-clause
family. Cumulative recorded-frame state is 734/1647 and 739/1602 fully-read
premises, 656/599 truth-scope vetoes, and 12/7 stack-ready stories. No TEST
look was spent.

---

# Session 18 (2026-07-21): Phase B reader 6 — negative-antecedent ground conditionals; the contrapositive is free; all gates NEUTRAL

One independently revertible increment (`cb3c955`, pushed) introduced the
delphi campaign's sixth premise-reader class. After the safety correction
below, its supported surface is **“If NAME is not P, then NAME is Q”** as the
new kernel fact `GroundConditional(entity, pred, then_pred,
then_polarity)` — semantics ¬P(e) → Q(e), the negation consumed as STRUCTURAL
skeleton so `pred` holds plain P, and a name never rides `Conditional.cls`
(the plan's pinned boundary). **pytest 1985 → 1995, scratch lint 0 errors,
curated 65/65; all eight benchmark slices snapshot-diffed NEUTRAL (the fact
kind touches model/patterns/schemas, so the full matrix ran as live blast
radius), and folio-with-logic is item-level neutral in OUTCOME AND REASON on
both splits (train 20 correct / 1 persistent poisoned-text wrong / 473
declined; holdout 1 / 0 / 424). No TEST look was spent.**

**Post-review safety correction:** the literal-`he` reader has been removed.
It asserted that `he` denoted the antecedent subject without consuming resolved
coreference evidence; for example, “If Alice is not taller than Bob, then he is
happy” could confidently assert that Alice was happy. The safe current surface
is repeated-name only. The original landed measurements are historical; the
corrected reader-6 delta is +2 / +0 fully-read premises and −2 / 0
truth-scope vetoes (dev-train / dev-holdout), with no Leon bycatch. The
correction passes all 2,004 tests, scratch lint (0 errors), and curated 65/65.

#### What landed, and the finding worth keeping

The safe pack rule serves the repeated-name surface (`If Marvin is not from
Earth, then Marvin is an extraterrestrial`, pinned by `same_lemma` — the 9i
precedent). Pronoun consequents remain unread until their referent is
represented as evidence. Both spans refuse negation, coordination, and
either/neither marking, so the
measured coordinated surfaces (Mike/Emily/Clyde/Thomas/Carol) stay
whole-unread; a different consequent name fails `same_lemma`. One
`unless`-free fire synth (gc + explicit ¬P(e) ⊢ Q(e)) completes the contract.

**The contrapositive ((¬P→Q) ∧ ¬Q ⊢ P) needed NO synth**: the Stage 9i
reductio engine assumes ¬P, the unless-free synth emits Q, the collision
with a stated ¬Q refutes the hypothesis, and P commits — pinned as
`test_contrapositive_comes_free_via_reductio`, and the reason the fire synth
must never grow an `unless`. The permissive fold's if-antecedent
`Membership('leon','degree')` leak is no longer hidden by an unsafe whole read;
it remains a separate sub-verdict reader problem.

#### Movement, and the measurement caveat

Corrected incremental movement is +2 / +0 fully-read premises and −2 / 0
truth-scope vetoes (dev-train / dev-holdout); the item-level movers are the
two Marvin items, and no verdict converts — Marvin still needs the compound-cls
universal, so stack-ready stays 12 / 7 stories. Banked pending coreference
evidence: the positive `he` surface, the negative-consequent `they` variant
(`If Nancy is not a teacher, then they are not paid by the school`, one train
story), and the `she` twin.
The three standing banks (`_naive_singular`, CamelCase names,
verbal-universal asks) re-checked at zero joins.

⚠ **The Phase A movement classifier was REGENERATED this session** (the
original was throwaway, per the plan). It reproduces the premise universe —
the metric scope is the ACTIONABLE DECLINE POOL, 1647/1602 premises —
fact-bearing, truth-scope vetoes, hazards (quarantine counts FACTS,
collision counts items), and every reader's incremental movement EXACTLY,
but its absolute fully-read total sits a constant −4/−11 below the recorded
scale at both endpoints. Compare DELTAS, not absolute totals; the full note
and the rebuilt script's definitions are in the reader-6 ROADMAP record.

**Next lever**: reader 7 should price one narrow passive or relative-clause
family per the Phase A build order (passive has the stronger balanced
marginal estimate), then re-survey compound generics and `entity-in-raw-if`.
Cumulative state is 732/1647 and 733/1602 fully-read, vetoes 658/605,
stack-ready 12/7 — all numeric Phase C thresholds still bind.

---

# Session 17 (2026-07-20): direct kinetic energy +2 rows @100%; one formula shape stays explicit; TEST holds

One independently revertible, pack-only physics increment adds translational
kinetic energy for a directly stated mass and velocity. **difg DEV 73 → 75
committed at 100% precision**; every other DEV/suite snapshot is item-neutral,
curated is 65/65 in two fresh processes, lint has 0 errors, and pytest **1951 →
1953**. All three aggregate-only TEST fingerprints are unchanged: difg **15
correct / 0 wrong / 92 declined**, GSM8K **13 correct / 1 persistent wrong /
1305 declined**, and SciBench **0 correct / 0 wrong / 168 declined**.

#### `kinetic energy = 0.5 * mass * velocity**2` — direct operands only

Session 16 supplied every prerequisite: compound `m/s` tokenization, the
canonical velocity dimension, `moving`, and full qualified formula keys.
This session therefore adds only declarative formula data. The exact `kinetic
energy` key cannot be borrowed by bare, gravitational, rotational, or
relativistic energy asks. A synthetic 3 kg × 4 m/s probe yields 24, while the
generic physics consumer continues to bind operands by unit rather than order.

The formula deliberately references only `mass` and `velocity`. A question
that states mass, distance, and time could derive velocity mathematically, but
`rulekit/formulas@1` declares one explicit expression and one operand set per
quantity. The existing whole-list contract therefore rejects the unread
distance/time values instead of silently composing the speed formula. A
synthetic negative probe pins that boundary.

The DEV corpus contains the same direct kinetic-energy question twice. Bench
counts both rows, hence 73 → 75, while snapshots key both copies to the same
question-derived ID and report one `SOLVED` ID (`8b9b4219aeb7`). This is a
pre-existing corpus/snapshot bookkeeping quirk, not two reasoning paths; do not
mix a snapshot-key migration into a formula increment.

**Next lever**: the remaining classical kinetic-energy row needs two things in
one bought increment: the `s` time symbol must canonicalize to the existing
seconds dimension, and formulas need guarded alternatives selected by a
uniquely satisfiable referenced-dimension set (`mass+velocity` versus
`mass+distance+time`). That is a schema/consumer increment, not another formula
line. Survey its cross-formula value before building it. Force remains blocked
by vocabulary exposure and contradictory Coulomb answer scaling; density still
conflicts with the one-canonical-unit-per-dimension contract. The separately
scoped text answer kind remains the other honest frontier.

---

# Session 16 (2026-07-20): momentum +1 @100%; compound units are whole tokens; three TEST firewalls hold

One independently revertible difg physics increment lands the previously
banked compound-unit tokenizer change with its first real buyer: linear
momentum. **difg DEV 72 → 73 committed at 100% precision**; every other
DEV/suite snapshot is item-neutral, curated is 65/65 in two fresh processes,
lint has 0 errors, and pytest **1948 → 1951**. All relevant aggregate-only TEST
fingerprints are unchanged: difg **15 correct / 0 wrong / 92 declined**,
GSM8K **13 correct / 1 persistent wrong / 1305 declined**, and SciBench
**0 correct / 0 wrong / 168 declined**.

#### `momentum = mass * velocity` — `m/s` is one semantic operand

The tokenizer now preserves compound scientific symbols and exponent-bearing
units as one token: `m/s`, `m/s^2`, and `cm^3`. The branch is structural and
precedes ordinary word tokenization; it does not know any unit vocabulary.
That closes the phantom-exponent hole where `m/s^2` used to emit a free-standing
count `2`. An unregistered compound symbol remains unknown and declines, so
force and density do not become reachable merely because their typography is
preserved.

Pack data gives `m/s` one identity, `meter_per_second`, and maps that identity
to the new `velocity` dimension. The generic physics binder can therefore read
mass and velocity by units, then evaluate the declarative `mass * velocity`
formula. `momentum` joins the exact physics-quantity gate; `moving` is admitted
as ordinary verb data. A synthetic 6 kg × 7 m/s probe yields 42, while a second
velocity declines under the existing duplicate-dimension guard. The difg buyer
commits 32 for 4 kg × 8 m/s.

The lexical admission had known exposure: `moving` occurs in one GSM8K TEST
item, and `momentum` occurs in two SciBench TEST items. Both aggregate-only
looks were spent and neither commitment fingerprint moved. The tokenizer still
fuses slash-shaped prose such as `installed/hung`; as in the banked measurement,
that can change the fully-read diagnostic (GSM8K dev-train 39.4% → 39.3%) but
produced zero answer-status changes across GSM8K, ASDiv, SVAMP, MAWPS,
SciBench, and FOLIO DEV.

**Next lever**: direct kinetic energy is now a small pack-only buyer:
`0.5 * mass * velocity**2` can solve the velocity-stated item using the exact
`kinetic energy` key. A second kinetic-energy item states distance and time
instead; it should continue to decline until formula alternatives are designed
as a separate mechanism. Force still has its TEST vocabulary exposure and
Coulomb output-scale contradiction; density still conflicts with the
one-canonical-unit-per-dimension contract.

---

# Session 15 (2026-07-20): gravitational potential energy +1 @100%; formula keys preserve every modifier; TEST holds

One independently revertible difg physics increment adds gravitational
potential energy and replaces the one-modifier formula-key render with the
reader's existing full-qualified phrase render. **difg DEV 71 → 72 committed at
100% precision**; every other DEV/suite snapshot is item-neutral, curated is
65/65 with fresh-process determinism, lint has 0 errors, and pytest **1946 →
1948**. Both aggregate-only TEST fingerprints are unchanged: difg **15 correct /
0 wrong / 92 declined**, GSM8K **13 correct / 1 persistent wrong / 1305
declined**.

#### `gravitational potential energy = mass * 9.8 * distance` — full phrases are keys

Session 13 preserved one modifier with `{q.qualifier} {q}`. That is sufficient
for `maximum wavelength` but lossy for a deeper compound: `gravitational
potential energy` carries both `gravitational` and `potential`, while the
single `qualifier` feature exposes only one. The generic present, imperative,
and past-qualified physics asks now resolve `{q.qualified}` instead. This
pre-existing renderer returns the complete folded phrase with its head lemma
canonicalized; a bare noun still renders as its lemma, and every existing
one-modifier formula key is unchanged.

The exact three-word key selects the near-Earth formula from data. A 5 kg
object at 10 meters computes exactly **490 J** through the existing mass and
distance dimensions; `height` needs no duplicate dimension because its stated
unit already supplies distance. `energy` joins the physics quantity gate, while
`gravitational` and `potential` are adjective data. Newly reachable kinetic,
rotational-kinetic, bare-energy, and shorter potential-energy asks all decline
at exact formula lookup. A synthetic negative probe pins that the shorter
`potential energy` key cannot borrow the gravitational formula.

**Next levers**: the clean potential-energy buyer is consumed. Kinetic energy
and momentum still need compound velocity-unit tokenization; force has TEST
vocabulary exposure and poisoned Coulomb output scaling; density conflicts with
the one-canonical-unit-per-dimension contract. Repeated-dimension families retain
their recorded blockers. The next honest choice is therefore a fully bought
`_TOKEN` + compound-unit formula class or the separately scoped text answer
kind—not an unbought reader enabler.

---

# Session 14 (2026-07-20): power formula +1 @100%; partitives resolve noun/verb polysemy; both TEST firewalls hold

One independently revertible difg physics increment adds average power as
declarative formula data and closes the reader gap in `joules of work`.
**difg DEV 70 → 71 committed at 100% precision**; every other DEV/suite
snapshot is item-neutral, curated is 65/65 with fresh-process determinism,
lint has 0 errors, and pytest **1944 → 1946**. The aggregate-only TEST checks
both held: difg's first recorded regression fingerprint is **15 correct / 0
wrong / 92 declined**, while GSM8K remains **13 correct / 1 persistent wrong /
1305 declined**. GSM8K fully-read exposure rose 376 → 379 but commitments did
not move.

#### `power = energy / time` — an old blocker expired, then exposed the real one

The formula was explicitly parked when the physics consumer could read only
the final question: `What is the power if ...?` moves the `if` clause into a
premise. Formula-level `scope: document`, independently bought in Session 11,
now makes the two unit-bearing operands available, so `power` joins the physics
quantity category and its formula uses the existing energy/time dimensions.
`joule/joules` is admitted as the canonical energy unit; the arithmetic-power
ask remains more specific and its regression probe still computes 2^10.

The first pack-only draft still declined. `work` genuinely has noun and verb
senses, but coverage arbitration tied: under the false verb trial it borrowed
the measured energy as a subject and the later duration as an object. The
reader now mirrors its existing article-noun filter with the already-declared
`partitive` category. A noun/verb ambiguity governed by a partitive preposition
selects its existing noun candidate; the kernel names only the structural
category, while English `of` remains YAML data. Outside that context ordinary
`work` remains verbal. Synthetic probes pin both paths.

**Rejected before code:** Coulomb force looked like the clean first buyer for a
commutative repeated-dimension reducer, but its reachable gold set is poisoned
by lost answer scale. One row expects the SI value **2.81 N**; another represents
**8.99 × 10^9 N** as the bare payload **8.99** after the corpus builder drops
units/scales. One honest formula cannot satisfy both. Do not key output scaling
on ask wording or land the repeated-charge mechanism through this class.

**Next levers**: power consumed the last obvious single-formula reuse unlocked
by document scope. Repeated-dimension formulas remain the A3 frontier, but the
thermometer, double-slit, Carnot, and Coulomb families each have a separately
recorded language/gold blocker. The `_TOKEN` compound-unit change remains
banked until independently bought, and the text answer kind remains its own
kernel+judge increment.

---

# Session 13 (2026-07-20): Wien formula +1 @100%; qualified present quantities keep their formula key; SciBench TEST holds 0 wrong

One independently revertible A3 increment adds modifier-preserving selection
for present/imperative physical quantities plus Wien's displacement formula.
**SciBench dev 5 → 6 committed at 100% precision**; every other DEV/suite
snapshot is item-neutral, curated is 65/65 with fresh-process determinism,
lint has 0 errors, and pytest **1941 → 1944**. The aggregate-only SciBench TEST
look was spent: **0 correct / 0 wrong / 168 declined**. Fully-read TEST coverage
is 1.2%, but no item committed, so the increment survives the precision hold.

#### `maximum wavelength = b / temperature` — the modifier is routing data

The generic `What is <physics_quantity>` and imperative asks used to collapse a
compound noun to its head: `maximum wavelength`, `typical wavelength`, and bare
`wavelength` all selected the same key. They now preserve the reader's existing
`qualifier` feature; the physics consumer and its whole-document accounting
guard normalize the empty qualifier for bare quantities with the same `strip()`
boundary. Existing bare `frequency`/`speed` formulas therefore remain stable,
while the new exact key is `maximum wavelength`. A synthetic sibling proves
that `typical wavelength` cannot borrow Wien's law.

The buyer states its 288 K temperature in a premise, so the formula explicitly
reuses `scope: document`. Its expression stores the physical Wien constant with
the answer's `10^-5 m` output scale folded in, following the existing de Broglie
and photon-frequency convention. `surface` is now noun-sensed: ordinary
noun+noun condensation still reads `surface area`, while the same unambiguous
sense can be possessed in `Earth's surface`. The six non-target corpora were
neutral under the vocabulary/sense change: GSM8K 104/0 + 40/0, ASDiv 44/0,
SVAMP 30/0, MAWPS 9/0, difg 70/0, and FOLIO 0/0.

**Rejected before code:** the constant-volume gas-thermometer class has clean
arithmetic golds but `triple point` currently reads `triple` as the numeric
multiplier 3. Source-scoped repeated-dimension roles would not fix that parse;
shipping the class would also require a separate declarative lexicalized-number
phrase mechanism. Do not weaken physics' all-values accounting or zero-multiply
the stray value. Reopen the thermometer only after that phrase mechanism has an
independent buyer.

**Next levers**: the clean qualified single-dimension buyer is consumed.
Repeated-dimension formulas remain the A3 frontier, but select a class whose
complete parse is already honest; the thermometer and double-slit rows each
have an additional numeric-language blocker. The `_TOKEN` compound-unit change
remains banked until independently bought, and the text answer kind remains its
own kernel+judge increment.

---

# Session 12 (2026-07-20): frequency formula +1 @100%; the first premise-scope reuse; SciBench TEST holds 0 wrong

One independently revertible A3 increment adds the general imperative
physical-quantity ask plus the declarative photon-frequency formula.
**SciBench dev 4 → 5 committed at 100% precision**; every other DEV/suite
snapshot is item-neutral, lint has 0 errors, curated is 65/65 with fresh-process
determinism, and pytest **1937 → 1941**. The aggregate-only SciBench TEST look
was spent from the main checkout: **0 correct / 0 wrong / 168 declined**.
Vocabulary raised its fully-read ceiling **1 → 2**, but the new readable item
still declined: zero transfer and zero damage, so the increment survives the
precision-hold rule.

#### `frequency = c / wavelength` — Session 11's schema is independently bought

This is the first independent reuse of formula-level `scope: document`; it
needs no kernel change. `frequency` opts into premise readings, the wavelength binds
by the existing `distance` dimension, and `nanometer → meter` is conversions
data. The expression yields the coefficient in `1e14 Hz`, so the speed-of-light
constant is explicitly scale-folded to `2.99792458e-6`, the same output-scale
discipline used by the de Broglie nanometre formula. The buyer computes
**4.73755** against typed gold **4.738**.

The general `Calculate <physics_quantity>` ask is shorter than the existing
change/eponymic constructions, so their more-specific readings still win. Its
one reachable frequency sibling states `207`, `1`, and `2` but no distance;
dimension binding makes it decline rather than treating any number as a
wavelength. Synthetic probes pin the `nm` symbol, an extra premise duration,
and non-distance values. Lexical admission had real DEV exposure (`light` 31
rows, `frequency` 19, `nm` 23), yet all six non-SciBench corpus diffs were
item-neutral.

The full gate initially failed because a synthetic test copied the corpus's
complete final sentence even though its magnitudes were invented. The
executable corpus-string firewall caught it; the test now asks for the
frequency “of the laser,” preserving the mechanism without embedding benchmark
text. This is constitution rule 3 enforced, not prose.

**Next levers**: the clean single-dimension premise buyer is consumed. Many
remaining A3 candidates need repeated-dimension roles (initial/final pressure
or temperature, two charges, multiple slit distances); build that only with a
class whose whole reachable gold set preflights cleanly. The `_TOKEN`
compound-unit change remains banked until independently bought, and the text
answer kind remains its own kernel+judge increment.

---

# Session 11 (2026-07-20): projectile formula +1 @100%; operand scope becomes formula data; SciBench TEST holds 0 wrong

One independently revertible A3 increment landed (`09a72ab`): the past-copular
qualified-quantity ask plus the declarative `initial speed` projectile formula.
**SciBench dev 3 → 4 committed at 100% precision**; every other DEV/suite
snapshot is item-neutral, lint has 0 errors, curated is 65/65 with fresh-process
determinism, and pytest **1932 → 1937**. The aggregate-only SciBench TEST look
was spent from the main checkout: **0 correct / 0 wrong / 168 declined**, the
same aggregate as both prior fingerprints. This is zero transfer and zero
damage; the increment survives the precision-hold rule.

#### Formula-level operand scope — the failed broad draft became schema

The first correct-looking implementation made every `physics` formula read all
premises. Its DEV diff was **1 SOLVED / 2 BROKE**: both entropy answers began
reading unrelated numerical assumptions from their boilerplate. That draft was
not landed. `rulekit/formulas@1` now carries `scope: question|document`, default
`question`; only `initial speed` opts into `document`. The registry freezes the
scope beside each expression, the consumer scans premises only for an opted-in
formula, and value accounting grants the whole-document exemption on that same
field. A formula taking the exemption must decline on every unused premise
value. Synthetic probes pin an extra duration, a repeated distance, and an
unregistered qualifier as declines.

The buyer is the general vacuum-projectile inversion
`sqrt(distance*g/sin(2*angle))`. Degree inputs reach canonical radians through
the existing conversion table; metre symbols reach the existing distance
dimension through lexicon plural data; `sin` is a whitelisted safe-evaluator
function. The ask resolves the compound formula key `initial speed`, never bare
`speed`, so the exposed GSM8K siblings `average speed` and `final weight` remain
item-neutral rather than borrowing the formula.

**Next levers**: formula-level premise scope now exists, so another one-class
A3 candidate may use clean earlier-sentence operands without widening every
formula. Still preflight every reachable sibling and every typed gold first;
many survivors need repeated-dimension roles rather than premise scope. The
`_TOKEN` compound-unit change remains banked until independently bought, and
the text answer kind remains its own kernel+judge increment.

---

# Session 10 (2026-07-20): de Broglie formula +1 @100%; SciBench TEST holds 0 wrong; the 65-item suite gate is repaired

One independently revertible increment landed (`cf539f5`): the eponymic
physical-quantity ask plus the declarative de Broglie wavelength formula.
**SciBench dev 2 → 3 committed at 100% precision**; every other DEV/suite
snapshot is item-neutral, lint has 0 errors, and pytest **1929 → 1932**.
The aggregate-only SciBench TEST look was spent from the main checkout:
**0 correct / 0 wrong / 168 declined**, byte-identical aggregates to the
previous fingerprint. This is zero transfer and zero damage; the increment
survives the precision-hold rule.

#### `cf539f5` — named quantity grammar, dimension binding unchanged

`ask/physics-eponymic-quantity` reads the construction as structural slots:
preposition + proper name + `physics_quantity`. The full phrase becomes the
formula key (`de broglie wavelength`), so another eponym reaches the SAME
grammar and then declines unless pack data defines it. The input stays on the
existing safe path: `eV` is a number-form of `electronvolt`, conversions@1
scales it to canonical joules, and the formula binds by the energy DIMENSION,
never position. An extra count and an unregistered eponym are pinned declines.

**Gold precision rejected two larger-looking classes before code:** the
second Carnot-efficiency row's exact 0.1072 sits outside the typed judge's 1%
band around gold 0.11; a Coulomb-force sibling drops its scientific-notation
exponent and would score the correct SI result wrong. One formula class must
survive ALL of its reachable siblings, not merely have one clean buyer.

#### The curated-suite invocation was stale, not the 65 cases

Session 9 added eight reference cases and the separate `projects/curated`
project that loads `packs/reference`. The active CI/mining commands still ran
the shared suite through `projects/gsm8k`, which deliberately does NOT load
that pack: live output was 57 correct + 8 declined, and bench exited 0. The
correct gate is now `--project projects/curated`: **65/65**, including the
fresh-process determinism check. Active CI, project commands, and both Claude/
Codex mining instructions now name that project; historical 52/52 records stay
historical. Do NOT "fix" this by loading reference into GSM8K — that would
widen a benchmark project's behavior to repair a command.

**Next levers**: continue A3 one-class formula growth, but preflight every
reachable sibling against the typed-gold tolerance first. The clean one-input,
same-question buyer was consumed here; many remaining candidates need premise
readings (operands live in an earlier sentence) or repeated-dimension roles.
The `_TOKEN` compound-unit change remains banked until independently bought;
the text answer kind remains its own kernel+judge increment.

---

# Session 9 (2026-07-20): SciBench ATTEMPTED — first 2 commits ever @100%; gsm8k TEST 92.3 → 92.9%; the reference tier lands (lookup + DuckDB aggregates)

Three landed commits, each through the full gate and walked on TEST
(`b57f562` LaTeX reader + entropy pair, `eca7e41` B1 reference lookup,
`7978ff5` B2 DuckDB aggregates), main fast-forwarded and pushed. **scibench
dev 0 → 2 committed at 100% precision** — the corpus's first commits since
its safety-gate days ended (the 0-commit expectation is RETIRED in
methodology §3b / CLAUDE.md / project.yaml; **FOLIO is now the sole
expect-0-commits gate**). All five other corpora byte-NEUTRAL through every
increment. pytest 1872 → **1929**, curated suite 52 → **65/65**. TEST looks
ledgered: **gsm8k 92.3% → 92.9%** (13/1 — one FREE TEST solve from the new
lexicon, no new wrong), **scibench TEST 0 wrong across 168** (zero transfer,
zero damage — the entropy class is dev-only, the fourth zero-transfer
corpus).

#### `b57f562` — the reader stage, and the accidental safety made structural

`kernel/mathtext.py` transcribes `$...$` LaTeX spans BEFORE tokenization.
The old 0-commit record was held up BY ACCIDENT — the tokenizer shredded
`$3.5 \times 10^{6} \mathrm{~J}$` into phantom counts value-accounting
could not consume. The reader keeps that safety structurally: **whole-span
conservatism** (one unrecognized construct → span verbatim → the old
decline) and an **object-identity fast path** (no backslash-command / `^{`
→ the SAME string object; the five non-LaTeX corpora were proven
byte-identical from a detached-HEAD worktree baseline, never assumed).
`_TOKEN`/`_DIGIT` untouched — unit exponents (`dm^3`, `m/s^2`) remain the
documented compound-unit increment.

- **The reader alone bought 0.** The buyer shipped with it: the entropy
  pair (golds 67/92) via `ask/physics-quantity-change` ("Calculate the
  change in <q>"), formula key **'entropy change'** (unreachable from the
  what-is ask — q/T is the Δ, never the absolute), and NEW scale-to-
  canonical binding in the physics consumer: linear via conversions@1
  (25 kJ → joule), affine via the merged token's **LABEL** ("100 degrees C"
  already carries `label: 'C'`; the pack row `{from: c, to: kelvin}` takes
  it to canonical). Ambiguous reach (two read dimensions) binds nothing.
- ⚠ **`gold: typed` on scibench is LOAD-BEARING.** Its golds are book
  answers rounded to 2-3 s.f.; the float path's TOL=1e-6 scores every
  CORRECT commit wrong (66.997 vs "#### 67"). And a 2 s.f. gold can sit
  outside even the typed 1% band (gold 2600 vs exact 2548.6) — **check
  |exact − gold| ≤ TOL + 1% BEFORE naming any scibench buyer.**
- 'energy' admitted: its physics-ops.yaml refusal ("no formula fires")
  expired with the entropy formula; exposure re-measured, gates arbitrated.

#### `eca7e41` / `7978ff5` — the reference tier (difg's dataset capability, re-homed)

**The dict/DuckDB split is the design**: point lookups compile into the
FROZEN registry (`rulekit/reference@1` → `reg.reference`, the conversions
pattern — a frozen dict beats SQL by ~10⁴ on lookups); SET questions
("total population of Europe in 2020" — membership JOIN + aggregate) go to
DuckDB (`rulekit/reference/db.py`, outside kernel/), whose tables DERIVE
from the same frozen mappings so determinism is inherited: one cached
connection per registry fingerprint, sorted insertion, **`SET threads TO
1`** (parallel SUM reorders float additions between runs). `duckdb` is an
optional extra; absence → the consumer DECLINES. difg's LLM-retrieval half
and trend projection were NOT ported — a year-less ask against a time
series declines (compile stores no year-less key), an out-of-series year
declines: an estimate is not a fact.

- **Packs may not shadow, and the fix is promotion**: 'area' existed in
  difg-mined AND the new pack — co-loading them was impossible until the
  word moved to core-english (the shared base both require). Found only
  because test_difg_mined's fixture co-loads; a project-level compile
  cannot see a cross-pack collision its own pack list avoids.
- The engine has **NO text answer kind** — capital-of lookups and
  superlatives ("largest country") are blocked until one exists (a
  kernel + judge design, its own increment).

#### Parked unbought, and the process traps

- `find`/`estimate`/`predict` imperative senses moved 16 scibench items
  from "no question found" to readable — and measured **0 SOLVED on all
  seven slices**. Parked in the session scratchpad
  (`imperative-senses-unbought.patch`); re-apply only WITH an ask that
  buys. [[enabler-must-be-bought]], enforced against my own increment.
- ⚠ **Never pipe pytest through `tail` in a background shell** — exit 0 is
  tail's, and it masked a real guard-coverage failure until a foreground
  re-run. The guard ratchet then caught BOTH new consumers' unprobed
  branches; golden rows + direct probes now ship WITH a consumer.
- `uv sync` DROPS extras the venv had ad hoc (pyarrow, fastapi) — resync
  `--all-extras` or bench/pytest die mid-gate.

**Next levers**: A3 formula growth over the 80-item "no ask shape" pool
(110 of 524 fully normalize; one CLASS per increment, gold-precision check
first); the `_TOKEN` compound-unit increment (unlocks pV=nRT); a text
answer kind.

---

# Session 8 (2026-07-20): svamp dev 13 → 30, asdiv 43 → 44, TEST look #1 spent, precision held

Five landed commits (`f50b94a` comparative, `5700e3c` relational,
`0792d85` animate coreference, `749d514` qualifier parity, plus two BANK
notes), each gate-clean on all nine DEV slices. **svamp dev 13/0 → 30/0**,
**asdiv 43/0 → 44/0**; gsm8k dev-train / mawps / scibench / folio NEUTRAL
item-by-item throughout; holdout 40/0, suite 52/52, difg 70/0, lint 0
errors. pytest 1843 → **1872**. ZERO confident-wrongs added anywhere, and
three LATENT ones removed.

**Two increments were built, gate-rejected and reverted** (the animate
stack, then the qualified fold alone). The animate stack later landed
UNCHANGED once its three exposed wrongs were fixed. That sequence is the
session's main lesson and is recorded below — a rejected increment is
often correct code sitting on broken ground.

#### `5700e3c` — the relational stage, and the pattern it confirms

**THE ENGINE'S CONJUNCTION HANDLING IS PER-CONSTRUCTION.** That is the
session's most transferable finding, now measured twice in two commits:
the SVO fold reads "A and B" fine, but the EXISTENTIAL premise dropped
its second conjunct (`f50b94a`) and the ANCHORED RELATION failed its
match outright (`5700e3c`, minting nothing at all). Each construction has
to earn conjunction separately. **Before designing any premise reader,
probe whether the singular form already works and only the conjunction is
missing** — both times that was the actual gap, and both times the
handoff's prose had described something broader.

The 13 items behind the value-accounting guard were **three mechanisms,
not one** ([[a-cluster-is-not-a-class]] again): 7 Baker + 4 Jake + 2
school. Only the 4 Jake items were relational.

- **The reader**: `arithmetic/anchored-relation-conjoined-measures` — both
  conjuncts share the ONE trailing standard. `distinct_measure` is checked
  on BOTH conjuncts (the elliptical self-reference can appear in either
  independently).
- **The holder hint**: reading the relation DERIVES the subject's
  quantities, so 'peach' gains a second holder and `label-difference`'s
  exactly-one-SHARED-holder discipline refuses. **Measured: the reader
  ALONE bought 0** — it moved the 4 items from guard-veto to
  consumer-decline, a lateral move. The held ask names the holder, so the
  consumer now reads it.
- ⚠ **THE FALLBACK IS THE LOAD-BEARING PART.** The hint is used ONLY when
  the named entity holds BOTH measures, and otherwise IGNORED — never a
  decline. `who` binds the question's SURFACE holder, which legitimately
  fails to match a fact key when the SCENE holds the quantities ("does the
  school have" binds 'school' while both facts sit on `world`). Declining
  on an unresolved hint would have REGRESSED `f50b94a`, the commit
  immediately before it. Falling back is byte-identical to pre-hint
  behaviour, so no path is made less safe.
- **Free wins, the sign the seam was right**: 4 of the 8 conversions are
  OUTSIDE the targeted form-A pool — they ask directly about the derived
  quantity ("How many apples does Jake have?") through PRE-EXISTING asks
  that only ever needed the relation read. All 8 verified individually
  against golds, not trusted from the aggregate.

#### `f50b94a` — the comparative stage

**SVAMP TEST looks #1 AND #2 SPENT (user-directed), and the pair is the
result.** Look #1 at HEAD: 246 items, 5 correct / 1 wrong / 240 declined,
precision **83.3%**. Look #2 at HEAD~1 (distinct fingerprint, both in
`snapshots/test-ledger.jsonl`): **byte-identical aggregates**. So the
lone confident-wrong is **PRE-EXISTING**, precision **held exactly**, and
the increment ships on evidence. ⚠ A first-ever TEST look on a corpus is
UNINTERPRETABLE ALONE — "1 wrong" condemns nothing when the rule is
precision-HOLD and no baseline exists. Budget two looks for the first
look at any new corpus, or the number cannot be acted on.

**Zero transfer, now on a third corpus.** 2 dev conversions → 0 TEST
conversions, exactly the folio look-#4/#5 lesson. Do not schedule the
next svamp look off dev-conversion count.

#### The stage, and the three framings the measurement corrected

The session-7 plan ("conjoined-existential READER landed WITH a
measure-vs-measure difference ask + consumer") was right in outline and
wrong in all three specifics — each correction found by probing, not
reading:

- **"Conjoined existential premises are unread" is too broad.** The SVO
  fold ALWAYS read the conjunction ("The basket has 7 red peaches and 8
  green peaches" mints both, `measure_qualifier` included) — 134 dev
  items. Only the existential surface dropped conjuncts, a 38-item class.
  The fix is an ASYMMETRY CLOSED, not a new capability.
- **The ask and consumer already existed.** `label-difference` +
  `ask/how-many-more-label-comparative` have handled two measure labels
  under one shared holder since the ratio-split-premises candidate — but
  only with the existential tail ("...are there?"). The held tail
  ("...does Steven have?") had no ask. So the increment is ASK-ONLY on
  that half: no kernel change, no consumer change, and the consumer's
  exactly-one-SHARED-holder decline-safety covers it unmodified.
- **The open |diff|-vs-decline design decision is MOOT.** SVAMP dev has
  **ZERO** genuinely reversed comparatives: all 11 candidates resolve
  FORWARD once ask-time quantities bind (the apparent reversals came from
  reading initial/`made` counts instead of `sold`/final ones). No
  measured buyer either way, so `label-difference`'s existing `abs()`
  stands. Do not reopen this without a reversed item in hand.

#### Invariants minted — do not relearn these

- **WORD ORDER IS THE GATE for the held comparative, and it is
  load-bearing.** Requiring `than MEASURE` BEFORE the auxiliary
  structurally excludes the 63-item aux-first family — verb-vs-verb
  ("did he lose than he gave"), time-vs-time ("than on tuesday"),
  entity-vs-entity ("than Jill"). That family contains the measured
  MISREADING HAZARD "How many more games does Katie have than her
  friend?" (gold 62 = (57+39)−34, an entity difference over a measure
  FOLD); a rule reaching it commits 57−39=18. Pinned by
  `test_aux_first_comparative_is_not_this_class`. Do NOT relax the tail
  to reach those items.
- **The enabler was bought, and the measurement is why.** The ask ALONE
  converted **0 of its 22-item form-A pool**. Landing it solo would have
  been the two-infra-increments mistake a third time; the reader is what
  buys it. Always measure the half you are about to land ALONE.
- **A synthetic test still needs LEXICON nouns.** The first draft used
  'widget'/'gadget' and failed all four reading assertions — an unknown
  word mints no fact, so the test fails for reasons unrelated to the rule.
  "Synthetic" means an invented SCENARIO, never invented VOCABULARY.
  Check `reg.plural_to_singular` before writing the fixture.

#### `0792d85` + `749d514` — the animate stack LANDED, and the parity bug behind it

**The stack below was rejected, then landed unchanged once its three
exposed wrongs were fixed.** svamp dev 23 → **30/0** (+7, all seven Baker
items); asdiv 43 → **44/0** from the parity fix. The reverted-then-landed
sequence is the record worth keeping: the coreference code never changed,
only the ground under it.

- **`slot_not_category`** — NEW where-predicate (opt-in per rule, like
  `distinct_measure`): a relation's STANDARD must not be a TIME PERIOD.
  Applied at 4 anchored-relation sites.
- **The attribution guard** — a BARE event over PARTS-ONLY state declines.
  Answering it needs source-marked transfer, deliberately absent.
- **The qualified fold** — a BARE ask asks for the WHOLE; fail-closed on a
  stated whole, unconditional for events.
- **The comma-less if-split**, banked twice, finally cashed: it is
  DOWNSTREAM of coreference (its promoted clause reads "he sold 158
  cakes"), which is exactly why it measured 0 buyers both times.

**`749d514` — THE QUALIFIER SPLIT WAS PAIRWISE, so odd-length part lists
stranded their last conjunct.** The split fired only on a key COLLISION,
and re-keying both sides REMOVED the bare key they collided on, so the
third sibling found nothing to collide with and was stored BARE — a
silently dropped qualifier. n=3 and n=5 stranded; n=4 and n=6 were clean
(the 4th rescues the 3rd). **The parity prediction was made and confirmed
BEFORE the fix** — that is what proved the mechanism instead of the
symptom. Now order-independent, pinned at four arities.

⚠ **Two of my own diagnoses in this file were WRONG, both from testing
with words the engine does not have.** "n-ary conjunction is unread
(~118 items)" was `pear` missing from the lexicon — 3- and 4-item
UNqualified lists always read fine. Before believing any reading defect,
check `reg.lexicon` / `reg.plural_to_singular` for every content word in
the probe. This is the `widget`/`gadget` lesson, and it has now cost two
mis-scoped entries here.

#### ⛔ The record of the first attempt (kept: it is why the guards exist)

**It was built end-to-end, it works, and it does not ship.** Gate:
svamp **+7 SOLVED** (form A 6 → 13 — all seven Baker items), gsm8k /
asdiv / svamp each **DECL→WRONG 1**. Rule 3 is not discretionary, so it
was reverted whole. Re-landing it needs the measure-fold fix below FIRST.

What was built (all four pieces are needed together, in this order):

1. `animate` category in core-english (parent: noun, 48 person-nouns) —
   membership is a SOUNDNESS claim, not vocabulary. Three deliberate
   exclusions: **'player'** ("MP3 player" is a DEVICE — the documented
   trap that once cost 2 GSM8K items), **'cook'** (verb sense; the
   'paint'/'work'/'second' precedent), **'king'** (name-like).
2. `animate_pronoun` category (parent: pronoun, [he, she, him, her]) —
   the kernel has NO gender or person feature (a pronoun unit carries
   only `number`), so without this gate the fallback binds 'it' to a
   person noun.
3. `document.py` `_animate_candidates` + a ZERO-NAME fallback in
   `_bind_discourse` (needs `reg` threaded to both call sites). ⚠ The
   zero-name ordering is the whole safety argument: `deixis.resolve`
   under the constant metric needs a UNIQUE winner, so adding candidates
   to a NON-empty set could silently UNBIND a working binding. Firing
   only when no name exists cannot do that. Verified by probe: binds
   'Baker…He', refuses 'basket…He', refuses 'Baker…It'.
4. `_split_leading_clause_commaless` (the twice-banked if-split) and
   verb-scoped `label-difference` (`_verb_total` on a non-state ask verb,
   mirroring the `difference` consumer's own split). SVAMP asks the SAME
   baker premises both ways — "did baker SELL?" (11) vs "did baker MAKE?"
   (78) — so the ask verb is the ONLY thing separating those golds.

**WHY IT FAILED, and it is not the coreference.** Binding the pronoun
makes previously-unread sentences READ, and they are then MISREAD by a
pre-existing weakness. NULL CONTROL, run at HEAD with the pronoun
replaced by a NAME: the asdiv shape commits **3 (gold 7)** and the gsm8k
shape commits **10 (gold 17)** with none of this code present. Two of the
three "new" wrongs are LATENT CONFIDENT-WRONGS THE ENGINE ALREADY HAS —
currently masked, by accident, behind a coreference failure.

⚠ **The masking generalises, and it is the real headline.** Every unbound
pronoun is potentially hiding a misreading. The system's zero-wrong
record is partly held up by sentences it fails to read at all, so ANY
future reading improvement can expose latent wrongs. Expect this; run the
null control (substitute a name, measure at HEAD) before blaming the new
code.

**THE BLOCKER IS THREE MECHANISMS, NOT ONE — corrected by building the
fix and measuring it.** The first version of this note said "qualified
measures do not fold into the bare form" and named that as the next
increment. IT WAS BUILT, IT GATES CLEAN, AND IT IS NOT ENOUGH — do not
rebuild it expecting to unblock the stack:

- **asdiv grapes — the qualified-part fold. SOLVED by the patch below,
  which is safe but 0-BUYER ALONE** (all six corpora NEUTRAL, so it must
  not land by itself). Two halves in `_entity_total`'s collection loop:
  (a) when the entity holds NO bare STATE quantity, adopt its qualified
  STATE siblings as the anchor — FAIL-CLOSED on a stated whole, because
  "14 blue + 26 purple, and 200 jellybeans in the jar" must stay 200,
  never 280; (b) ALWAYS extend `events` with qualified siblings — an
  event is a delta, never a restatement of the whole, so it cannot
  double-count. Verified: "15 brown bears and 24 white bears" → 39, and
  the grapes item moves WRONG(3) → decline.
- **gsm8k carpenter — UNTOUCHED, a different bug.** "Last month, he made
  three fewer tables than this month" mints `carpenter/month=13`: an
  anchored relation whose STANDARD is a TIME PERIOD, not an entity. It
  should decline and instead invents a month quantity.
- **svamp farmer — likely UNWINNABLE as written.** "had 105 green
  tomatoes … in his garden … picked 137 tomatoes" needs picking to DEBIT
  the garden (gold 39 = 176-137), but 'pick' folds as an ACQUISITION, so
  the parts and the pick sum to 313. Making that come out right is
  SOURCE-MARKED TRANSFER — a mechanism `_entity_total`'s own docstring
  and docs/negative-results.md record as deliberately NOT existing. Do
  not treat this item as a buyer for anything.

So re-landing the animate stack needs the carpenter relation-standard
fix as well, and must accept the farmer item staying declined. The
qualified fold should land WITH whichever of those first gives it a
buyer — never on its own.

#### Next up (measured, not started): Class A is pronoun coreference, NOT premise reading

Of the original 13, the 4 relational are DONE (`5700e3c`). What remains:

- **Class A — the Baker family, 7 items, the largest single lever.**
  Blocked by **PRONOUN COREFERENCE**, which is not what it looks like.
  `baker` is lexically `['noun']` (an occupation), so "Baker made 157
  cakes. **He** sold 158 cakes." fails with *"'He' (pronoun) needs a
  refers and none was found"* — while "Ana made… **She** sold…" works,
  because 'ana' is an UNKNOWN word that defaults to NAME. Verified by
  probe: substituting the name for the pronoun makes the item read.
  The general fix is admitting a subject COMMON NOUN as a pronoun
  antecedent — linguistically correct and not a lexicon hack — but it is
  CORE shared machinery under all seven corpora, a far wider blast radius
  than anything landed this session. Do NOT "fix" it by deleting 'baker'
  from the lexicon: that is word-specific fitting, and it would break
  ordinary "the baker has 5 cakes" readings.
- **The comma-less leading if-split stays BANKED, and now we know WHY its
  buyers never cash.** It was implemented again this session and reverted
  again: it correctly promotes "If he sold 158 cakes and 147 pastries" to
  a premise, and the Baker items STILL decline, because the promoted
  clause's 'he' cannot corefer. **The if-split is downstream of the
  coreference fix, not independent of it** — land them together or not at
  all. (Session 7 banked it on a 0-buyer measurement; this is the reason
  behind that number.)
- **Class C — 2 items**: "465 more girls joined the school" is an unread
  ACQUISITION EVENT on the scene holder. Its own small class.
- The remaining declines are the partitive "pages of math homework"
  qualifier gap (a DIFFERENT reading class — the qualifier is lost, only
  `page=2` mints) and 2 fold conflicts.

---

# Session 7 (2026-07-19/20): the SVAMP campaign opens — survey, two precision fixes, one banked enabler

The SVAMP mining campaign is OPEN. **SVAMP dev (754 items) is now a MINED
corpus and no longer an independent cross-corpus gate for GSM8K work** — its
salt-cut TEST reserve (246 items, `build_corpus.py`, SALT `svamp-test@1`) is
the precision measure, spent like any TEST look. ASDiv / MAWPS / SciBench /
FOLIO stay unmined gates, and GSM8K's dev slices now gate SVAMP-mined
changes in the reverse direction (nothing new is fitted to them).

Two commits landed and PUSHED (`5bf5517`, `35ac745`), both PRECISION fixes
for confident-wrongs LIVE on main before this session — every one of the
nine DEV slices NEUTRAL on both, folio-with-logic byte-identical item-by-
item. pytest 1833 → **1843**. svamp dev stays **13/0** (0 SOLVED — that is
the point: these were wrongs the corpora never phrased).

**Numbers at HEAD:** unchanged everywhere — gsm8k 104/0 + 40/0 + suite
52/52, asdiv 43/0, svamp 13/0, mawps 9/0, scibench 0/0, folio 0/0, difg
70/0, folio-with-logic 20+1 / 1-0. lint 0 errors.

#### The survey (recreate per methodology §4; per-item JSON was scratch)

741 declines = **473 no-ask-shape + 426 vocab-blocked** (178 items blocked
by ONE word, 142 by two; the top "unknown word" `t` is the hyphen-split of
"t-shirt" — 19 items, one Razorback story family — a READING artifact, not
vocabulary). The no-ask-shape pool clusters: **182 if-lead fused questions**
("If she had grown 3 trees initially How many more trees died…" — no comma,
capitalized wh mid-sentence), **~150 comparatives** ("how many more N1 than
N2…", 124 standalone + overlaps), remainder small shapes (geometry
"how deep/what is the length", grouping, pieces-of). Coverage factorization
43.5% fully-read × 4.0% hit-rate — the gap is machinery, not vocabulary.

#### What shipped (the class, one paragraph each)

- **`5bf5517` — a specific instance's count is not a per-container rate.**
  "A book has 2 chapters. The second chapter is 36 pages long. If there are
  a total of 67 pages in the book, how many pages are in the first
  chapter?" (gold 31) committed **67** — the single-entity distributive-
  container branch read the qualifier='second' fact as a per-container rate;
  with that closed it committed **36** — ask/how-many-in-place DROPPED the
  'first' it never binds. Fixes: `_distributive_rate_source` extracted to
  module level in saturate.py (the distributive-container-total synth's own
  gate — now the ONE definition), applied in `_container_contents_synth`'s
  rate table (filtered BEFORE the uniqueness check) and the consumer's
  `holds_rate`; and the in-place ask binds
  `entity_qualifier: "{place.qualifier}"` (the entity-side twin of
  `measure_qualifier` — the consumer's qualifier_store machinery existed
  all along, nothing bound it). Pinned in test_group_total_container.py.
- **`35ac745` — an anchorless events-only fold has no license to commit.**
  "Randy has some blocks. He uses 52… how many did he have at the start?"
  committed **−52**; even "Rina uses 4 blocks. How many blocks does Rina
  have?" committed **−4** on plain GSM8K machinery. Two guards in
  `_entity_total` (shared fold — full nine-slice gate): a state-category
  Predication whose dobj was bound by a bare quantifier
  (`Predication.dobj_unquantified`, NEW field, deliberately NOT in `key()`)
  declines the fold in BOTH directions ("has some, buys 4" is as
  unanswerable as "has some, uses 4"); and a negative signed-event sum
  declines (summed in plain Python — a declined probe must not enter the
  arithmetic log's value accounting). Pure acquisitions ("bought 4 and 3"
  = 7) untouched. Pinned in test_anchorless_fold_guard.py.

#### Invariants minted — do not relearn these

- **The modal have-artifact.** "Jerry HAD TO SELL boxes" mints the same
  have/box Predication shape as "has SOME blocks" — the FIRST version of
  the anchor guard keyed on the bare shape and the ASDiv gate broke
  (`9d175f1131ff`, correct → declined). The distinguishing evidence is the
  quantifier-role obligation targeting the dobj, recorded at mint time in
  learn.py — structural (role name), never a word list. A guard keyed on a
  fact SHAPE must ask what else mints that shape.
- **`abs()` in a test assertion is a blessed wrong.** test_mining_
  increment_25's coreference test asserted `abs(value) == 8` because the
  engine has always answered −8 there; the guard exposed it. Its real
  concern (cross-mention entity identity) is now asserted against the
  STORE. Grep tests for `abs(` before trusting an old committed value.
- **An enabler must be bought — measured live this session.** The comma-
  less if-split fired on 175/182 fused questions and cashed ZERO (177
  still miss ask shapes post-split); its only two commits were the two
  wrongs above. REVERTED and banked, exactly the two-infra-increments
  lesson from the GSM8K run.
- **A cluster is not a class, twice.** "If-lead" (182) decomposed into
  ~114 vocab + 39 comparative + 24 geometry once probed; "comparative"
  (150) decomposes into measure-vs-measure (55) + existential/qualifier
  (43) + verb-vs-verb / time-vs-time wearing an entity surface (42) +
  elliptical goal (10). Neither shared surface was a shared mechanism.

#### BANKED: the comma-less leading if-split (design is complete, do not re-derive)

Sibling of increment 53's `_split_trailing_clause_commaless`, as a fallback
INSIDE `_split_leading_clause` (both call sites in `split_question` benefit).
Cue: a MID-SENTENCE CAPITALIZED ask-cue token (the capital does the comma's
job — lowercase embedded 'how' never splits); the promoted clause must carry
a digit; the FIRST qualifying boundary wins, NOT the trailing form's LAST —
the errors are asymmetric (early split leaves junk on the QUESTION side and
declines; late split folds question words into a PREMISE and mints facts
from unasserted material). A capitalized name carrying a modal sense
('Will', 'May') is skipped by the digit test when it opens the sentence.
Land it ONLY with measured buyers — the 39 comparative if-lead items are
the named candidates, after the comparative stage exists.

#### Next stage (scoped, measured, NOT started): comparatives

The class is blocked BELOW the ask — conjoined existential premises are
unread: "In a school there are 34 girls and 841 boys" mints ONLY girl=34
(the conjunct is lost); "7 red peaches, 71 yellow peaches and 8 green
peaches are in the basket" mints ~nothing (a Membership). The designed
stage is a conjoined-existential READER landed WITH a measure-vs-measure
difference ask + consumer (the existing `difference` consumer is entity-
vs-entity under one measure; this one is two measures under one holder/
scene, where "baseball cards vs Ace cards" and "green vs red peaches" may
both resolve as ONE measure with two `measure_qualifier`s). OPEN DESIGN
DECISION, measure before choosing: reversed-direction asks ("how many more
girls than boys" where boys win) — decline as presupposition failure vs
answer |diff|; SVAMP's adversarial items punish the wrong choice. The Nell
baseball-cards item is a MISREADING hazard (two sentences read wrong, one
fact on the wrong entity), not a buyer.

#### Carry-forwards

- The two spent-look policies stand (gsm8k TEST 92.3%, folio look #5).
  **No SVAMP TEST look yet** — nothing was mined INTO svamp dev; spend the
  first look only after the campaign's first coverage increments land.
- The vocabulary admissions list (survey top-40) is cheap coverage but
  EVERY admission goes through `packs/difg-mined/quarantine.yaml` first.
- "t-shirt" (19 items) is a tokenizer/condense READING class, not
  vocabulary — same lesson as CO2/MP3: hyphenated compounds need data,
  read them where the data is.

---

# Session 6 (2026-07-19): Stages 9h + 9i + 9j — elimination, reductio, identity

Three stages landed (`6b2ba94` tokenizer + `18fad9e` 9h, `ea1a266` 9i,
`fc60a2d` 9j), every commit NEUTRAL on all nine DEV slices;
folio-with-logic dev-train **15 → 20** ([400] Ocellated +1, [128/129]
Bubbles +2, [100/101] Islip +2). pytest 1803 → **1833**. Stage detail:
`projects/scratch/ROADMAP.md` §9h–9j.

**Numbers at HEAD:** folio-with-logic dev-train **20 correct / 1 poisoned**,
dev-holdout **1/0**. All benchmark baselines unchanged (gsm8k 104/0 + 40/0 +
suite 52/52, asdiv 43/0, svamp 13/0, mawps 9/0, scibench 0/0, folio 0/0,
difg 70/0).

**TEST look #5 SPENT (user-directed, 2026-07-19): 1 correct / 1 wrong /
283 of 285 — aggregates IDENTICAL to looks #3–#4. Precision 0.5 held, no
revert; but 9 conversions from EIGHT distinct stories (incl. three
designed inference stages) transferred ZERO TEST items — the look-4
zero-transfer lesson is now measured twice.** A TEST conversion needs an
entire story STACK to line up; single-story conversions will not move
TEST at 285 items. Do not schedule look #6 off conversion count alone —
TEST movement needs breadth-first premise-reader coverage of the
convertible pool's common blocker classes, a different campaign. Full
note: ROADMAP §"TEST look #5".
⚠ Operational: a TEST-look script MUST be a FILE, not a heredoc — the
jobs>1 spawn pool re-imports the main module and a stdin script crashes
every worker (caught before any information leaked; ledger was clean).

#### 9j in one paragraph (the identity stack)

`synth/name-prefix-alias` (both names must be fact subjects; unique
extension) + `synth/name-head-sortal` (join-driven: a ≥2-word,
partitive-free name declares its head's sort ONLY when the story already
quantifies over that head) + the restricted stative-'have' universal and
its do-support denial (a modus-tollens pair keying 'have {q}' identically,
anaphoric PP consumed but never keyed) + `synth/conditional-modus-tollens`.
The 9e Alias copy synths and Stage 3 DS close the chain.

#### 9i in one paragraph (the S4 frontier is open)

The reductio engine lives in `consumers/logic_verdict.py`: an undecided
verdict atom is assumed each way in a throwaway store copy and
re-saturated; a quarantining closure refutes the hypothesis. It works
because the Bubbles derivation is LINEAR given `synth/modus-tollens` (new,
reusable — the Islip MT half now exists) and the `DisjunctiveConditional`
fire synths (exactly-one established, sound under both readings; NO
`unless` ON PURPOSE — the collision IS the contradiction signal). Two
traps already caught by tests, not corpora: no reductio under a
definite-description question (it would answer from atoms the Phase 0
gate just refused), and the fire synths must never fire on one true +
one undecided disjunct (Stage 3's exclusivity measurement).

#### What shipped (one line each)

- **Tokenizer** (`6b2ba94`): U+2019 folds like ASCII `'` — the curly
  apostrophe was DROPPED between tokens, so "Gould’s"/"Gould's" minted two
  different fact keys and two of [400]'s five refutations could never join.
  Surfaces stay verbatim; only the fold normalizes. gsm8k train has 271
  curly-apostrophe items, so its NEUTRAL gate was a real measurement.
- **9h** (`18fad9e`): `EnumeratedDisjunction` (n-way, INCLUSIVE — the
  numeral licenses exhaustiveness, never exclusivity), minted only when
  stated count == listed count (fail closed); consumed only by
  `synth/enumeration-elimination` (a saturate plugin — n-ary is
  inexpressible in the fixed-arity YAML synths). Guards pinned: no
  membership → nothing; any positive option → decided; >1 open → nothing;
  a quarantined option atom taints the entity.

#### Carry-forwards

- **Look #5 is SPENT** (see above). No look #6 without a new policy —
  conversion count is no longer the right precondition.
- **Islip [99]** (the temporal-existential item) needs event/time
  machinery — not an increment.
- **[8]/[9] William Dickinson** — corpus defect, unwinnable.
- **[144/145] do-support negation VR** remains the last named designed
  stage; the session-5 invariants below all still hold.

---

# Session 5 (2026-07-19, second half): FOLIO frontier 9d–9g — four conversions, four new stories

Four commits (`76810e1` 9d, `398e61e` 9e, `490a02c` 9f, `d66a78c` 9g), every
one +1 SOLVED / 0 BROKE on folio-with-logic and byte-identical on all eight
benchmark slices. pytest 1772 → **1803**. Stage detail lives in
`projects/scratch/ROADMAP.md` (§9d–9g); this section carries only what the
next session must not relearn.

**Numbers at HEAD:** folio-with-logic dev-train **15 correct / 1 poisoned**
(item 228, the standing proof the judge works), dev-holdout **1/0**. All
session-3/4 benchmark baselines below still hold (gsm8k 104/0 + 40/0 + suite
52/52, asdiv 43/0, svamp 13/0, mawps 9/0, scibench 0/0, folio 0/0, difg
70/0). lint 0 errors everywhere; scratch carries 8 warnings, all the
standing is/are-alternation class. **TEST look #5 count: 15 dev-train + 1
holdout of the ~20-21 the look-4 policy wants. Do not spend the look.**

#### What shipped (one line each)

- **9d** — `atom_variants` tail drop covers the REDUCED relative ("a van
  produced by Chevrolet" IS a van); the banked bare-plural disjunctive
  premise landed RESTRICTED with its first buyer (veto-lift).
- **9e** — `Alias` fact + 'known as' reader + two-direction copy synths;
  epithets refused by the definite-article gate; negated surface never
  matches by lit adjacency.
- **9f** — the appointive passive (`appointive_verb`, a SOUNDNESS category:
  resultative only, 'regarded/described as' must never join); the
  lead-nominal RUN extension in `atom_variants`; the verbal 'Some' premise.
- **9g** — `schemas.FactEmit.each` (per-item emission over an enumeration
  span, `{item}` reserved binding); the typed-enumeration rule gated on
  'type' so possessive enumerations stay UNREAD not misread; the 9b-banked
  De Morgan neither/nor reader, landed WITH its buyer as the bank
  prescribed.

#### Invariants minted — do not relearn these

- **Probe the matcher, not the consumer.** Every conversion this session
  came from a 10-line driver running candidates through `solve()` +
  `match_ask` over the near-frontier declines ("no logic fact decides it" —
  the conclusion already reads). Reachability is a whole-pipeline property;
  reading the consumer cannot answer it.
- **The subsumption trap, now general:** a rule ending in non-span tokens
  is SILENTLY DROPPED at `admit_rule_results` beside a sibling whose greedy
  span consumes a strict superset — the span swallows the trailing period
  (9e) and mid-sentence articles (9f). A new rule sharing a surface with
  the ground-copular family must claim every such skippable (opt
  `consume_skipped` tokens) or out-gate it on category depth. Both
  occurrences are pinned.
- **A banked zero is scoped to its reader-moment.** Stage 7 measured
  "participial levers = 0" against the then-current reader; 9d's buyer
  existed the whole time behind a premise that minted no droppable atom
  yet. Re-measure banked zeros after ANY reader change.
- **Walk the buyer's whole story** fired twice more (9d's qdisj, 9f's
  some-verbal): the fragment guard prices every unread truth-scoping word
  into the item, so a conversion's cost includes reading its story's
  bystander sentences.
- **Land a banked fix WITH its first buyer** paid out twice exactly as
  written (bare-plural disjunctive premise, De Morgan reader). The bank
  notes were precise enough to implement from — keep writing them that way.

#### Do NOT do next, with reasons

- **A folio TEST look** — 15+1 of ~20-21; the policy stands.
- **[400] (gold-true Ocellated)** without the n-way elimination stage — the
  enumeration deliberately does not claim exhaustiveness; committing from
  it without elimination machinery would be unsound.
- **Islip [99-101]** without identity machinery — modus tollens there needs
  `speedway(islip)`, which NO premise states; the route is name-shortening
  identity ('Islip' ≡ 'Islip Speedway'), an INFERENCE the 9e alias reader
  deliberately excluded. Design it as its own stage or not at all.
- **[8]/[9] William Dickinson** — missing-period corpus defect, unwinnable.
- **The 169 'Uncertain' text golds** — can never score correct; they are
  wrong-hazards, not opportunities. The convertible pool is 311 at HEAD.
- The remaining multi-item near stories each need a DESIGNED stage
  (ROADMAP §"after 9g"): n-way elimination, XOR-conditional reductio
  [128/129], do-support negation VR + negative-restrictor refutation
  [144/145]. Pick one deliberately at session start; none is an increment.

Survey/diff scripts were session-scratch (per methodology §4): the recipe is
`folio_survey.py` = run dev-train via `harness.bench.run_suite` with the
scratch registry, dump per-item outcome/reason/text to JSON, diff by idx.

---

# Session 4 (2026-07-19): the A/B/C plan landed — guard coverage 90/90, lint blind spot fixed, answer.py split

Three commits (0d35c31, e24ebb1, 31a9097), every corpus byte-identical
throughout — this session changed NO behaviour, only pinned and moved it.
All session-3 baselines below still hold at HEAD. pytest 1728 → **1772**.

- **A — guard coverage 49/90 → 90/90, ratchet at ceiling** (`_GUARD_FLOOR=90`,
  `_GAP_CEILING=0`). 18 gaps were text-reachable after all (found by probing
  the live matcher, not reading the consumer — the currency-ambiguity,
  found/now-has restatement, and `type: noun` span-unit tricks); 23 are
  direct `ConsumerContext` probes in `tests/test_consumer_guard_probes.py`,
  each with its unreachability reason recorded in `_COVERED_BY_UNIT_TEST`.
  ⚠ The six verdict consumers' "question states" guard is text-unreachable
  BY CONSTRUCTION: a final span must run to sentence end and never swallows
  a `span_blocks` word, and every verdict ask anchors `at_start` — probe it
  by truncating a real match's `consumed` tuple.
- **B — the linter's `nonstate_verb` blind spot**: `_TYPE_SENSES` had no
  entry, so the type read as "matches anything" and all 8 scratch errors
  were ONE false positive ({lit: is} vs a slot `_slot_ok` refuses). Fixed by
  mirroring `_slot_ok` (state category on BOTH surface and verb lemma).
  scratch lint is now clean and BLOCKING in CI.
- **C — answer.py 1,175 → 197**: folds to `kernel/totals.py` (811),
  measure resolution to `kernel/measures.py` (218). Every moved function
  verified BYTE-IDENTICAL against the pre-move file, mechanically.
  Import graph is one-way (measures→answer, totals→answer+measures);
  `_unit_price_from_total`/`_sign`/`_conversion_factor` live in totals —
  moving them is what keeps the graph acyclic. saturate.py's five deferred
  imports are now two top-level ones. NOTE: totals.py at 811 lines still
  exceeds architecture.md's ~400 budget — the violation moved, it did not
  vanish; splitting the fold family further is future work with the golden
  master already in place.

---

# Session 3 (2026-07-18/19): +27 correct answers, answer.py refactored 41/41, 0 new wrongs

**Baselines — all re-measured at HEAD, every commit gate-clean:**

| corpus | | corpus | |
|---|---|---|---|
| gsm8k dev-train | **104/0** | difg | **70/0** of 342 |
| gsm8k dev-holdout | **40/0** | asdiv | **43/0** |
| gsm8k TEST | 92.3% (**no look spent**) | svamp | **13/0** |
| curated suite | **52/52** | mawps | **9/0** |
| folio | **0/0** | scibench | **0/0** |
| folio-with-logic dev-train | **11 / 1 poisoned** | …dev-holdout | **1/0** |

pytest **1420 → 1728**. lint: gsm8k/difg 0 errors; scratch 8 (all false
positives — see task B).

#### What shipped

- **difg 44 → 70** (+26): angle conversions, percent change, ISO + spelled
  dates, geometric-measure costing, discounted/taxed totals, unit-converted
  rate costing, `seconds` literal-variant, hypotenuse, affine temperature,
  molar mass + derived quantities.
- **folio-with-logic 10 → 11** (Stage 9a) plus two precision fixes (9b, 9c).
- **`answer.py` 3,479 → 1,175 lines**, all 41 consumers extracted to
  `kernel/consumers/` behind `ConsumerContext` + a registry.
- **Guardrails**: `/api/doc` firewall hole, `--twice`'s false determinism
  claim, CI (`.github/workflows/ci.yml`), contractions moved to a pack,
  the `lit` alternation primitive + 3 lint checks.

#### Invariants minted — do not relearn these

- **Reading that needs DATA belongs where the data is.** `CO2` and `MP3` are
  structurally identical; only the element table separates them, and the
  tokenizer has no registry. A tokenizer-level formula pattern cost 2 GSM8K
  items before moving to `condense`. Same lesson as spelled dates.
- **`answer()` had SHARED code between consumer branches.** A block boundary
  drawn to "the next `if consumer ==`" swallows the **temporal origo**. The
  origo also SPLITS the file: 15 consumers above it never see the
  time-filtered store, 26 below it always do — hence two dispatch points and
  `time_scoped=True`, recorded per consumer at extraction.
- **A refactor must never launder its own debt.** `_declared_guards()` parsed
  only `answer.py`, so extracting a consumer deleted its guards from the
  denominator and coverage improved for free. It now scans `consumers/` too.
- **The guard denominator is 90, not 92.** The old figure came from the same
  naive boundary bug; verified against the pre-refactor file.
- **difg has mangled golds.** `What time is 90 minutes after 11:15 AM?` golds
  as `value=12.0, unit=':45 PM'` — an engine answering the bare hour scores
  CORRECT for the wrong reason. Also `1.2044` + `e+24` for molecules. And
  small-magnitude MONEY golds are unwinnable: `$0.27432` vs a `$0.27` gold
  fails the 1% relative comparator. Do not chase; do not "fix" by rounding.
- **Rule 3 was being broken.** 47 corpus sentences were in `tests/`, several
  added this session in files whose docstrings claimed "SYNTHETIC ONLY".
  `tests/test_no_corpus_strings_in_tests.py` now guards it with a 38-entry
  debt ledger (shrink it, never grow it).
- **`bare_form`'s `fold == lemma` test is a proxy delegating to lemma data**
  with 71 gaps; fixed fail-closed on the -s suffix (9c). The COVERAGE half
  (adding the 71 mappings) is still open and rewrites fact keys corpus-wide.

#### Do NOT do next, with reasons

- **`saturate.py` (1,903 lines)** — it already HAS the registry (`PLUGINS`,
  `saturate.py:1875`), but `_relations_synth` alone is **654 lines (34%)**, so
  extracting the other 11 plugins leaves ~850 and does not close the budget it
  is motivated by. Those 654 lines are an ordered fallthrough over four shared
  mutable indices where **reachability is the contract**
  (`saturate.py:590-593`); splitting converts an invariant statement order
  enforces into one a registry must. And there is NO characterisation net —
  the 654-line plugin is the least pinned of all (`synth/relation-to-quantity`:
  1 test mention). If ever taken on: build a store-level golden master first
  (assert the sorted `(kind, entity, measure, value, provenance.source)` set
  after `saturate()`), then task C below, then factor the anchor-lookup layer
  (`saturate.py:215-330`) into a `QuantityIndex` — a real seam, ~120 lines, no
  ordering risk. `learn.py` (1,551) is worse: one 661-line `learn()`, no
  registry at all.
- **A folio TEST look** — policy needs ~10 more conversions; there is 1 since
  look #4.
- **The remaining difg items** — the cheap ones are gone. Percent composition
  needs `composition` (GSM8K dev exposure) AND a bare single-symbol `O`, which
  would sweep in `B`/`C`/`K` as labels. Finance (3), proportion (2) and
  inclusion-exclusion (1) all need premise reading or new machinery.

#### Next up (agreed plan: A → B → C, in order)

- **A. Close the 41 guard gaps** — tests only. Per consumer: golden-master row
  where the guard is text-reachable, else a direct `ConsumerContext` probe
  asserting the decline (pattern: `tests/test_consumer_molar_mass.py`).
  Bookkeeping: `_GUARD_FLOOR` / `_GAP_CEILING` / `_COVERED_BY_UNIT_TEST` in
  `tests/test_consumer_golden_master.py`.
- **B. Fix the linter's `nonstate_verb` blind spot** — `_TYPE_SENSES`
  (`src/rulekit/lint/overlap.py:32`) has no entry, so `{lit: is}` reports a
  collision it cannot have. Clears all 8 scratch errors; then make scratch
  lint BLOCKING in CI.
- **C. Lift `answer.py`'s 981 helper lines out by theme** — `kernel/totals.py`
  (~640: the eight `_*_total` helpers), `kernel/measures.py` (~185: the five
  `_resolve_measure*`/`_check_req_unit`/`_measure_substance_guard` helpers),
  leaving `answer.py` ~195. Repoint 17 consumer imports; `saturate.py`'s five
  deferred imports become top-level. Byte-neutral everywhere. A before C so
  guards are pinned before they move.

---

# Session handoff — 2026-07-18 (session 2)

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
Always check `git status` / `git log origin/main..HEAD` before assuming push parity.

## GUARDRAIL FIXES + CI (2026-07-18, from an external review)

Four findings verified against the code and fixed; one deferred with reasons.

### The designer could read and overwrite TEST data over HTTP

`/api/doc`'s check admitted any path under a pack root **OR under the PROJECT
root** — the second disjunct is the whole project directory, `data/` and
`snapshots/` included. `GET` leaked TEST golds; `PUT` overwrote datasets and
baselines. Now an ALLOWLIST of exactly the pack YAML the UI is offered, shared
with the listing endpoint.

⚠ **MEMBERSHIP GUARDS THE REQUEST; CONTAINMENT GUARDS THE LIST — you need
both.** Resolve-and-compare alone does NOT contain the tree: a symlink planted
in a pack is listed by `rglob`, and since the request side resolves too, both
sides resolve to the same target and membership PASSES. `pack_documents` now
drops any entry resolving outside its pack root. Found by my own test failing.

The boundary is a PURE function (`resolve_editable_doc`) so it is tested with
no HTTP stack — the first test needed `httpx` and SKIPPED, and a security check
that runs only when a dependency happens to be installed is no check.

### `bench --twice` claimed a determinism check it could not make

Both runs shared one interpreter, so it could not see module globals, caches or
import-order effects. At the DEFAULT `--jobs 1` it was near-vacuous. Now: the
in-process pass runs ONLY at `--jobs > 1` (a real parallel-vs-serial proof),
and a second pass re-runs in a FRESH isolated interpreter comparing canonical
snapshots via a temp file. A child that fails for any reason is a FAILURE —
"could not verify" is not "verified". **Verified by fault injection**: a
process-dependent difference exits 3, and the old version could not have caught
it. `--twice` is now refused on aggregate-only slices.

### CI exists (`.github/workflows/ci.yml`)

Compile → lint → pytest → curated suite `--twice`. **It states what it cannot
check**: data is gitignored BECAUSE of the firewall, so CI can never run the
corpus gates that decide whether a change ships. Those stay local.
`projects/scratch` is information-only (8 pre-existing overlap-ties; a check
that starts red is not a check).

### Contractions are pack data

`_CONTRACTIONS` was the one place the kernel enumerated WORDS. Now
`rulekit/contractions@1` in core-english, passed to `tokenize(contractions=)`
rather than looked up, so that stage stays registry-free. **The registry sorts
longest-clitic-first because matching is by SUFFIX** — the old dict was
order-dependent on insertion order, which nothing guaranteed.

### DEFERRED: splitting the oversized kernel modules

`answer.py` 3479 lines, `saturate.py` 1903, `learn.py` 1551, against
`architecture.md`'s "≤ ~400 lines". The finding is real. **But "split by
consumer behind stable dispatch interfaces" is the highest-risk change
available here**: `answer.py` is where every guard lives, and this session
alone produced three cases where a plausible change to shared machinery was
wrong in a way only one specific test caught. A split with no behavioural gate
is the exact shape that ships a silent regression. If it happens: one consumer
at a time, each with the full eight-slice gate, and the honest FIRST step is
characterisation tests for the consumers that lack them — not the split.

## ⚡ WHAT CHANGED THIS SESSION — 20 NEW CORRECT ANSWERS, 0 NEW WRONGS

Thirteen commits, every one gate-clean across all eight slices, pytest
1420 -> **1504**, lint unchanged, **no TEST look spent on any corpus**.

| commit | what | effect |
|---|---|---|
| `ebfd7df` | **9a** verbal universal's restrictor folds like its copular twin | folio-logic 10 -> **11** |
| `9959edc` | **9b** 'neither' can no longer hide a negation in a phrase key | precision |
| `d34e7f7` | **9c** `bare_form` fails closed on the -s agreement suffix | precision |
| `c1eb77a` | difg angle conversions (degrees <-> radians) | difg 44 -> **47** |
| `7783c2a` | difg percent change (one signed formula, four spellings) | 47 -> **49** |
| `64436d7` | difg calendar (ISO dates as whole tokens, spans, day-of-year) | 49 -> **53** |
| `ed76df8` | difg geometric-measure costing (tile/fence) | 53 -> **54** |
| `17027a0` | difg discounted/taxed totals | 54 -> **56** |
| `232c384` | difg unit-converted rate costing | 56 -> **58** |
| `794d3e6` | difg 'seconds' literal-variant conversion ask | 58 -> **59** |
| `07faa2d` | difg right-triangle hypotenuse | 59 -> **60** |
| `52ccf8f` | difg temperature (affine, zero-point scales) | 60 -> **62** |
| `e580297` | difg calendar spelled dates | 62 -> **63** |
| `c298c1b` | **refactor**: spelled dates READ in condense, not parsed in an ask | 63, -1 ask |

### THE `lit` ALTERNATION — new matcher infrastructure (2026-07-18)

`lit` now accepts a LIST: `{lit: [sine, sin]}` matches any option. Six commits,
every slice byte-neutral throughout.

**Why it exists.** `core.yaml` had said for a long time that "there is no OR
primitive over match tokens", and worked around it. The blocker it kept hitting
is structural: **a category roots at exactly ONE sense** (`registry.py` raises
`CompileError` when a member lacks it), so the words that need alternating are
precisely the ones that can never join a category — 'any' is article-sensed,
'many' is interrogative (not a root sense at all), and 'second'/'average'/
'work'/'paint' are the documented traps where ADDING a sense broke a consumer.

**Categories are still preferred where they fit**, and the field comment says
so: a category NAME is refusable by `span_blocks` from other rules and visible
to blast-radius analysis; an alternation is deliberately neither.

**RANK NEUTRALITY is the load-bearing claim, and it is pinned by test.** An
alternation counts as ONE required token, consumes ONE unit, and contributes
ZERO gate depth — so collapsing N siblings ranks exactly as whichever sibling
would have fired. `rule_specificity` and `_ask_rank` are UNCHANGED and now say
why in-code. **Do not give alternations gate-depth credit** without re-gating
every collapsed family: it would break the identity that makes each collapse
provable.

**Enforcement is split, with no overlap.** A WHOLLY dead literal is refused by
`compile_registry` — it cannot be loaded at all, so `rulekit lint` (which needs
a compiled registry) could never see one. Two WARNING checks remain in
`lint/checks.py` for what still loads: `partially-dead-alternation` (some
options dead, so the token silently narrows) and
`alternation-should-be-category`.

⚠ Promoting the dead-literal check to a load-time error made the LINT check for
it unreachable, and it was deleted rather than left. That was caught by two of
its own tests failing — they could no longer BUILD their fixture. **A test that
cannot construct its own precondition is telling you the precondition is now
impossible.**

`alternation-should-be-category` has fired on every alternation landed so far
(trig `sine`/`sin`, three logic `is`/`was`) and each answer is now written in
the pack — which is its job. The recurring answer is worth knowing in advance:
a category CONTRIBUTES GATE DEPTH, so switching an alternation to a `cat` gate
would raise that ask's rank above the siblings it replaced and turn a provable
no-op into a ranking change. It also needs a SLOT, binding something no
consumer reads.

**Collapses landed:** trig `sine`/`sin`; logic `a`/`an` (4 asks → 2); logic
tense+article (8 asks → 3, including the two-dimensional `passive-agent` 4 → 1).
Each surviving id is a PREFIX of the siblings it replaced, so it still sorts
first among them and cannot lose a tie — id order is `match_ask`'s final
tie-break and is the one genuine non-neutrality of any collapse.

⚠ **ASK SIDE ONLY.** The premise rules' is/are split carries the Stage 8d
`.singular` fold (`-are` folds the restrictor, `-is` does not) and must never
be merged this way. Pinned by test.

**Still missing, deliberately: alternation over token SEQUENCES.** The "in all"
totality tails need a two-token run where a sibling ask has one slot; `lit:`
does not reach that and is not planned to. The five comments in `core.yaml` that
used to claim "no OR primitive" now say this precisely.

### The 12 dead literals — and the guard that now catches them

A bare `{lit: the}` / `{lit: a}` can NEVER match: articles are a SKIPPABLE
sense, so the skip loop walks past them. Twelve had accumulated in
`packs/arithmetic/rules/core.yaml`, all inside `opt:` groups whose only content
was the dead token — silent no-ops. **Deleted rather than "fixed"**: adding
`consume_skipped: true` (plainly the author's intent) would make all 12 START
matching and CONSUME a unit, and `len(match.consumed)` is the PRIMARY key of
both `_ask_rank` and `specificity` — a live behavioural change at 12 sites
dressed as a typo fix.

⚠ The lint walk must be FULLY recursive: a one-level version found 10 of 12,
because two are an `opt:` nested inside an `opt:`. Caught by diffing against an
independent measurement, not by reading the code.

### ARCHITECTURE REVIEW of everything after Stage 9c (done 2026-07-18)

Two refactors landed from it (`c298c1b`, `9f1a146`): **-6 asks, -1 consumer
op, -1 helper, -198 lines, zero behaviour change on all 8 slices.** The
recurring error was reaching for a second ASK whenever a second SURFACE FORM
appeared. Three cures, in order of preference:

1. **Read lower.** Spelled dates became a `condense` merge pass, so every
   date-consuming ask got them free (`c298c1b`).
2. **Gate wider.** Four percent-change asks became one via two categories --
   `percent_word` (nouns) and `change_direction` (VERBS; verb-parented
   categories already existed) (`9f1a146`).
3. **Check the gate you have.** `type: number` tests the VALUE KIND and never
   the sense, so it ALREADY matches count-merged '4 meter'. Three
   `type: counted` twins were strictly narrower and DEAD from birth
   (`9f1a146`). Pinned in test_measure_cost.py.

**An ask should enumerate STRUCTURE, never the ways English spells it.**

### The remaining generalisation, NOT built — it needs a decision

**Three data tables are the same table**, split by who READS them, not by what
they mean:

| table | shape | really |
|---|---|---|
| `conversions@1` | factor | `v * f` |
| `affine-conversions@1` | offset + factor | `(v + o) * f` |
| `calendar@1 span_units` | days-per-unit | `v * (1/f)` |

An affine map with `offset: 0` IS a pure factor, so **affine subsumes all
three**. And four consumers are the same consumer: `unit-convert` (`v*f`),
`affine-convert` (`(v+o)*f`), `rate-cost` (`(v+o)*f*rate`), and calendar's
span (`v/f`).

The split was NOT arbitrary -- `conversions@1` is read PAIRWISE by the
word-problem convertible-unit fold in every arithmetic corpus, which is why
calendar and affine got their own tables (a 'month -> day' or an offset row
there would change unit folding everywhere). **The right unification is one
`rulekit/scales@1` with a required `scope:` field**, so the fold reads
`scope: unit` rows only and the others are invisible to it. That is the
infrastructure this session kept working around.

**Cost/benefit, honestly:** it touches shared machinery under all 8 corpora
and buys ZERO new items. Do it when a FIFTH scale-shaped table is about to be
written -- that is the point where the workaround costs more than the fix.

**What does NOT generalise, and why the obvious move is wrong:** the five new
consumers are 152 lines with 16 decline paths, and only ~4 lines EACH are
arithmetic. Pushing that arithmetic into declarative `expr` strings (the
`geometry@1` model) would absorb the trivial part and LOSE the guards --
"decline if discount >= 1", "decline if a measure is <= 0", "decline if the
month is impossible". The real duplication is in the GUARDS, which repeat
three shapes 16 times: operand-is-numeric, operand-in-range, data-lookup-hit.
**A declarative guard vocabulary would pay; a declarative expression table
would not.**

### The seam lesson, because it cost a commit to learn twice

`e580297` shipped a spelled-date ASK with six slots plus a consumer branch to
rebuild a date from its parts -- one commit after the ISO-date increment whose
own message says *"THE INCREMENT IS A READER, not a rule"*. That is date
parsing duplicated into two layers with no business knowing about calendars,
and it scales by (date surface forms) x (asks that want a date).

`c298c1b` moved it to a `condense` merge pass, so the existing
`{slot: d1, type: date}` absorbs both spellings. Net -1 ask, -1 consumer op,
-1 helper, all 8 slices identical. **Two things fell out for free, which is
how you know the seam was right**: "1 January 2024" now reads (it was a
documented GAP -- the deleted ask took `type: name` and 'January' is a
`timeperiod` NOUN), and `ask/calendar-day-of-year` accepts spelled dates
though no variant was ever written for it.

**The general rule: if a new SURFACE FORM makes you write a second ask, the
reading belongs in tokenize/numbers/condense instead.**

**Current numbers:** gsm8k dev-train **104/0**, dev-holdout **40/0**, TEST
92.3% (untouched). asdiv **43/0**, svamp **13/0**, mawps **9/0**, scibench
**0/0**, folio **0/0**, difg **63/0 of 342**. folio-with-logic dev-train
**11 correct / 0 real wrongs** (the 1 "wrong" is item 228's FOL-verified
POISONED GOLD), holdout **1/0**.

### THE GATE CAUGHT A CONFIDENT-WRONG, and the fix was to build LESS

`rate-cost`'s first version added a transitive lookup over the conversions
table (it is a PAIR table: 'mile -> kilometer' and 'yard -> foot', nothing
joining yards to kilometres). It worked, and it shipped a wrong:

> "What is the total cost of 100 yards at $3 per km?" is EXACTLY $0.27432.
> difg rounded the gold to $0.27. The typed-gold comparator is TOL + 1%
> RELATIVE, which at that magnitude allows only ±0.0027. **The correct
> answer scores WRONG.**

So the chain's only DEV buyer was an item with a defective gold — an enabler
with no valid buyer. It was REMOVED, not kept-with-an-exception.

**Small-magnitude money golds in this corpus are unwinnable wherever the true
value has sub-cent precision.** The same rounding is invisible on the mile
items only because 1% of $48.27 is 48 cents. Do NOT "fix" this by rounding a
consumer's output to cents — that is fitting the comparator rather than
reading the question.

### difg's mangled golds — four items score correct for the WRONG reason

difg's builder mangled several typed payloads. These are traps in BOTH
directions and none should be counted as coverage:

- `What time is 90 minutes after 11:15 AM?` -> `value=12.0, unit=':45 PM'`.
  An engine answering the bare hour scores CORRECT without doing the
  arithmetic. Same for `What time is it 5 hours before 1:00 AM?`.
- `How many molecules are in 2 moles?` -> `value=1.2044, unit='e+24'`. The
  correct answer scores WRONG.
- The two `$N each` split-cost items are `text` golds.

### What is left in difg, measured

- **Proportion (2 items)** — "If a recipe for 4 servings needs 2 cups, how
  much for 6?" / "If 3 apples cost $2, how much do 12 cost?". ONE class
  (`B x C/A`), but BOTH need PREMISE reading: the leading if-clause splits
  and the premise mints no correspondence fact. Needs a new fact kind.
- **Inclusion-exclusion (1)** — same premise-reading blocker.
- ~~**Chemistry molar mass**~~ **DONE** (`50bc91a`, `8eed0b3`): difg 63 -> 70.
  A formula is one unit fused in **`condense`, NOT the tokenizer** — the first
  attempt used a tokenizer pattern and cost 2 GSM8K items on "an MP3 player",
  because **`CO2` and `MP3` are structurally identical** and only the element
  table separates them. The tokenizer has no registry, so no tokenizer-level
  pattern can be correct there. Reading that needs DATA belongs where the data
  is.
  **Still open in that cluster: percent composition** — needs 'composition'
  admitted (GSM8K dev exposure) AND a bare single-symbol 'O' to read as an
  element; allowing lone one-group formulas would sweep in 'B'/'C'/'K' wherever
  they are labels. Neither risk is measured, so the item stays declined.
- **Finance (3)** — present value, monthly payment, future value.

### The ambiguity tie: measured at 3 items system-wide, NOT worth fixing

`obligations.disambiguate` commits only a UNIQUE winner, so a SECOND
ambiguous unit anywhere in a sentence can tie the arbitration, mark every
ambiguous unit unresolved, and let the `ambiguity` guard veto before any ask
is tried. It blocks 2 of the 3 geometric-costing items ('cost' noun/verb,
'square' adjective/noun join 'much').

**Do not chase it.** Measured across all corpora: difg 2, asdiv 1, gsm8k 0,
svamp 0 — **3 items total**, against a change to the sense-arbitration core.
A structural interrogative-after-interrogative pre-filter was built and does
NOT fix it (reducing 'much' to one option still leaves the other tying two
ways). Reverted, banked.

### The one soundness finding worth carrying forward

`bare_form` (Stage 8f) is the WHOLE generic-vs-ground signal and decides by
reading `fold == lemma` as "uninflected" -- which is only as good as the lemma
data. **71 s-final verbs in the lexicon are their own lemma** ('lives',
'leaves', 'agrees', 'consists', ...), so the most inflected form in the
language passed the test: *"Rochelle lives in Europe"* minted a UNIVERSAL over
the class 'rochelle'. Fixed in `d34e7f7` by testing the SUFFIX too, fail-closed.

**The COVERAGE half is still open and is a real next increment.** Because
'lives' has no lemma mapping, its fact keys are still 'lives in europe', which
can never join the 'live in europe' an ask renders. Adding the 71 lemma
mappings is pack data, but it **rewrites fact KEYS across all seven corpora** --
its own increment, its own gate. `d34e7f7` makes it SAFE to do: with a mapping
in place `fold != lemma` refuses on the first test anyway, so the two compose.

### difg is the productive frontier — and here is how to find work in it

**Rank every decline by VOCABULARY COST** (how many unknown words block it).
That one measurement explains the whole corpus: the three cheap wins above
needed ZERO admissions; the chemistry cluster needs 4-5 each, which is why
`physics` stalled at 3/14. Recreate the script from this paragraph (`solve()`
each declined item, collect units with no senses).

**MEASURED AND READY, in value order** (each is a named CLASS, not a one-off):

1. **Geometric-measure costing — 3 items, the best remaining.** "How much does
   it cost to tile a 4 meter by 6 meter floor at $8 per square meter?" (192),
   "...plus 8% tax?" (207.36), "How much to fence a 4 by 6 yard at $5 per
   meter?" (100). ONE class: `cost = geometric measure x unit rate`. Needs a
   "W by H" dimension-pair reader and a word->geometry-quantity mapping in pack
   data (`area_verb: [tile, carpet, paint]` / `perimeter_verb: [fence]`) so no
   verb enters Python. Two SIBLINGS have `text` golds ("$64 each") -- not
   winnable, do not count them.
2. **Temperature (2 items)** -- affine, needs an `offset` on ConversionDef.
   The HANDOFF has long said "probably not worth it" and that still holds:
   `conversions@1` is read pairwise by the word-problem fold in every
   arithmetic corpus.
3. ~~Chemistry molar mass~~ — **DONE**, see above (difg 63 -> 70).
4. **Ailton passive-relative stack** — 3 pieces for 1 item, same story as
   S1a's existing conversion (bad transfer economics); stays deferred.

### Do NOT (all measured, all recorded)

- **[427] "plays for Bayern Munchen?"** — needs "Bayern is a team", which no
  premise states; a sortal-free conditional instantiation fails its own null
  control. Recorded in the 8g ROADMAP entry.
- **The locative bridge** — re-measured post-S1a/S2: completes NO stack
  (item 4 needs identity; item 174 needs junction-specific spatial
  inference). Re-measure only after new stacks land.
- **The reductio/case-analysis F/T pairs** (Federer 140/141, Bubbles 128/129,
  Tom-PhD 96/97, Jim-Knicks 47/48) — assumption-based reasoning, the S4
  frontier, not increments. 47's story also never mentions Jim (annotation
  hazard).
- **Poisoned golds**: dev-train 228 (scored "wrong" forever — it is the
  proof the judge works), base_conversion's 2, ASDiv London/Blair.

### The measurement harness (scratchpad scripts are GONE — recreate from this)

The folio-with-logic bench does NOT exist as a CLI path (folio-the-project
must stay logic-free). Recipe, ~20 lines: `load_project(projects/folio)` for
`dataset_items("dev-train"|"dev-holdout")`, `load_project(projects/scratch)`
for the registry, `run_suite(items, scratch.registry, jobs=8,
project_dir=projects/scratch)`. Gotchas that each cost a run this session:
**the script needs an `if __name__ == "__main__":` guard** (the spawn pool
re-imports the main module — without it, fork bomb); `ItemResult` fields are
`id/outcome/expected/got/reason/rules` (no index — enumerate); `report.counts`
is a PROPERTY, `report.aggregates()` a METHOD. Dump per-item rows to JSON for
before/after item-level diffs on DEV slices. For a TEST look: aggregates
ONLY, `record_test_look(projects/folio/snapshots/test-ledger.jsonl,
registry.fingerprint, report.aggregates())` — never store per-item TEST
results. Single-item fact-store dumps: `solve(text, reg)` + print
`result.store.facts` (the dump-the-facts discipline — never infer a
mechanism from the answer).

### Invariants minted this session (each is pinned by tests — grep before touching)

- **A measured ZERO is scoped to the JOIN it enumerated.** "Unknown-plural
  morphology bridges 0 pairs" was true of conclusion↔premise; the buyers
  lived premise↔premise. Before trusting (or re-deriving) a zero, ask which
  join the simulation ran, then dump one real item's fact store.
- **The `.singular` fold must stay SYMMETRIC**: the plural-agreeing family
  (quantifier+'are', bare plurals, 'some…are') folds on premises AND asks
  together; the -is/-was singular constructions must NEVER fold (their keys
  join ground atom preds verbatim — the 'lens' hazard). Decomposition sees
  through the attr (`atom_variants`); any new attr must decide this too.
- **`bare_form` (fold == lemma) is the verbal generic's agreement signal** —
  the verbal sibling of the copular rules' `{lit: are}`. Inflected/past
  verbs stay ground; pinned.
- **The titular merge takes head features from the NAME side**, accepts a
  mid-sentence capitalized KNOWN left word ('Salmon' is a lexicon fish), and
  refuses sentence-initial ones ("Members of Pappy's"). Gated on the
  `partitive` category — 'of' was already core-english pack data.
- **Article capitals never name** (senses.py, beside the Stage 7 quantifier
  exemption): the FOLIO wrapper embeds "The <Title> is…" with its capital,
  and a name-annotated 'The' made the same text stop echoing itself. Caught
  by the increment's own echo test — no corpus phrases it; keep the test.
- **Reading lifts the veto; content can be inert.** Three conversions now
  ([Regent St], [426], [185]) came from rules whose emitted facts decide
  nothing in the story — consuming the truth-scoping units IS the payoff.
  But the read must still be sound in case its keys ever join (8g's
  conditional is echo-exact flat keys, fail-closed variants pinned).

The full stage-by-stage record: `projects/scratch/ROADMAP.md` (Stages 8d–8g
+ look #4 + the banked-and-resolved drop note). Auto-memory mirrors this
condensed. Everything below this line is the 2026-07-17 handoff, still
valid for the difg/benchmark frontiers.

---

> ## ⚡ THE FOLIO CAMPAIGN IS CLOSED (2026-07-17): the buyer was MEASURED UNWIDENABLE, so
> ## look #3 was NOT spent — read `docs/negative-results.md` → "The FOLIO buyer is
> ## UNWIDENABLE" (the ladder table + the four suspect probes) BEFORE any folio work.
> - **Landed and LIVE** (`d8d41c3`): the story-grouped internal holdout (`group:` dataset column;
>   folio dev-train 494 / dev-holdout 425, 0 stories straddling; gsm8k byte-identical) + folio
>   baseline snapshots. folio stays the 0/0 logic SAFETY gate — that is its job, and it has
>   already paid (it caught a real bug on its first run).
> - **Reverted twice, stays reverted**: the full verdict-commitment increment (`88f6382`, v1) and
>   its copular-only narrowing (`bbfc03c`, v2) each passed EVERY DEV gate and each scored
>   **0 correct / 1 WRONG** on its folio TEST look (looks #1–#2, no attribution possible).
> - **Why closed**: every widening rung — full plural map (the 'citizens' family buys ZERO),
>   consume-only readers, conjunctive grounds, copular if-then universals, quantified/'some'
>   conclusion consumers with ∃-intro — simulates to the SAME 1 commit / 494 on dev-train.
>   FOLIO entailment needs restricted-class universals, EXCLUSIVE 'either...or' (a naive
>   inclusive-or reader manufactures a confident-wrong), case analysis, definite descriptions —
>   an inference-engine FRONTIER, not increments. The ~10-30-commit precondition for look #3 is
>   unreachable, so a third landing is forbidden by the same rule that forbade a thin one.
> - **The suspect probes are BANKED** (negative-results has the full evidence): tense collapse
>   EXONERATED (FOLIO's FOL is tenseless — keying on tense breaks two real DEV Trues); the
>   membership Atom fallback EXONERATED BY CONSTRUCTION (unreachable on wrapped items; the
>   pytest suite pins depend on it — do not drop it); 'no'-universal polarity SOUND (five
>   synthetic interaction cases). **ONE real hazard found: indefinite subjects** ("A Kelly bag
>   is ..." mints a ground atom; "...that A Czech is a European?" binds subj='czech') — the
>   likeliest TEST culprit, inside both reverted surfaces, dormant on main only because
>   verdicts don't commit. Any re-landing must first build the indefinite-article gate
>   (sense split + opt-in skipped-sense match flag; design in negative-results §3).
> - **The v2 KERNEL half is RE-LANDED for the scratch sandbox** (post-closure): Atom/Quantified,
>   span capture, verdict commitment + both judge flips + the fragment guard are on main again,
>   but `packs/logic` lives ONLY in `projects/scratch/` (ask/is-membership stayed in arithmetic)
>   — no benchmark project loads a verdict-producing rule, folio stays logic-free at 0/0, and
>   every gate re-measured NEUTRAL. This does NOT reopen the campaign: folio TEST is untouched
>   and the indefinite-subject gate is still unbuilt. En route the resurrection caught a REAL
>   kernel unsoundness: `_canonical_phrase` rendered merged compounds by bare head lemma, so
>   ADMITTING a modifier word silently loosened phrase keys ("X is a Czech conductor"
>   confidently yes'd "Is it true that X is a CHORAL conductor?"). Fixed + pinned
>   (test_qualified_phrase_survives_KNOWN_vocabulary) — the Fiedler discipline had been
>   resting on vocabulary ignorance.

> ## ➡ FOLIO IS BUILT, BENCHED AND LANDED — **919 DEV items, 0 correct / 0 WRONG** (`f7b059c`).
> ## **It caught a real confident-answer on its first run**; the fix took TWO passes (`b1db917` was the WITNESS fix, `b5655ca` the class).
> ## Frontier 2 is REOPENED but is NOT a `committed` widening: see "what FOLIO actually buys".

### ⚠ Three things the last handoff asserted that turned out to be FALSE — check, don't inherit
1. **"the two files are WRITTEN and committed"** — they were UNTRACKED. Nothing was lost, but the
   gate did not exist in the repo. `git status` before believing a handoff's push claims.
2. **`conj-train.json` is NOT "identical to head behavior"** — it is the ORIGINAL ~14-correct
   baseline and reads **90 SOLVED** against head's 104/0. It is a fine floor (0 BROKE still means
   what it says) but `NET +90` is drift, not your increment. For a true before/after, snapshot the
   prior commit — do not trust the committed baseline as "current".
3. **`bench --snapshot` CRASHED on every `gold: typed` project** (`TypedGold is not JSON
   serializable`), so the `rulekit diff` ship gate was silently unavailable for difg — the ACTIVE
   frontier — and folio. Fixed in `d0a818e`; GSM8K snapshots verified byte-identical.

### ✅ THE PRECISION WORKLIST IS EMPTY — **zero confident-wrongs in the whole system**

| corpus | | corpus | |
|---|---|---|---|
| gsm8k dev-train | **104/0** | asdiv | **43/0 (100%)** |
| gsm8k dev-holdout | **40/0** | svamp | **13/0 (100%)** |
| gsm8k suite | **52/52** | mawps | **9/0 (100%)** |
| gsm8k **TEST** | **12/1 (92.3%)** | difg · folio · scibench | 44/0 · 0/0 · 0/0 |

**All 7 triaged wrongs are gone** (`2b8430b` `a874887` `89dde5a` `a9184d7` `95571e6`) — the handoff
called them "the hard tail"; reading them refuted it (`docs/negative-results.md` → "The 7
confident-wrongs triaged"). ONE TEST look was spent in the whole run, and it HELD. **The 1 gsm8k
TEST wrong is the stable §3a unseen shape, present since look #1** — it is not addressable from DEV.

**What this does NOT mean.** Six of the seven were fixed by DECLINING, not by reading better:
source-marked transfer, fractional transfer and temporal arithmetic all remain unbuilt, and the
items that needed them (7 · 19 · 170 · 17) are unreachable, not solved. Precision is now a
CEILING, not a floor: the next increment is a coverage one, and the first wrong it ships will
come from here.

**⚠ Two of the five fixes were the SECOND-attempt version. Both first attempts passed ALL SIX
CORPORA and were still wrong** (the holder-count fraction guard; "start-state + no events →
decline"), caught only by unit tests encoding contracts no corpus phrases. **The corpora are a
SAMPLE; the tests are the SPECIFICATION.** Grep the tests for the behavior you are about to change.

**Still unbuilt, and each is now the only route to its items** (do not re-brief them as guards —
the guards are landed and the reading is what is left):
- **source-marked transfer** — "Rachel picked 3 apples FROM HER TREE" must debit the tree. Worth
  2 ASDiv items (7, 19), which now DECLINE. See `packs/arithmetic/rules/start-state.yaml`.
- **fractional transfer** — `transfer-prepositional` models transfers correctly (two legs, signing
  from category data) but its amount slot is `type: counted`. Needs the rule AND a possessor-based
  synth; sizing against the pool is a different, wrong quantity. Worth 1 ASDiv item (17).
- **noun-after-preposition arbitration** — "books about plants" stays AMBIGUOUS, so it declines
  rather than reading 170. Solving it means core sense machinery under every corpus.
- **temporal arithmetic** — the closed month/time seam. The Blair/London item ALSO has a POISONED
  GOLD (below), so it is worth 0 even if built.

**⚠ ASDiv's London/Blair age gold is WRONG — never chase it.** The gap is invariant at 5, so
`B_then = 2·L_then` with `B_then − L_then = 5` → London was **5**, six years ago. **The gold (6)
answers "how many years ago"; the text asks "how old was London then".** A correct engine scores
WRONG. It now declines (`95571e6`), which is the only available win.

### GSM8K is DONE and stays a regression floor
dev-train **104/0 (100%)**, dev-holdout **40/0**, curated suite **52/52**, **TEST 92.3%** (12/1 —
the session high; the subject-gapping fix solved a "gave X to Y and bought Z" TEST item). Both
engine halves (ask-shape, reading) measured out as a LONG TAIL — GSM8K coverage is closed, and the
next lever was always a DIFFERENT corpus. That is now the whole game. Proof: `docs/negative-results.md`
→ "The reading gap is a LONG TAIL"; brief `docs/reading-gap.md` is CLOSED.

### FRONTIER 1 (active): difg domain-mining — `projects/difg/`, difg-DEV 0 → 44 correct, 0 wrong (of 342 items)
NINE domains are solved via one reusable **template**:
*select an operation/formula by NAME via a category-gated ask, bind the operands, apply a general
operation* — words in YAML, operations in a consumer branch, no per-domain Python.

| Domain | Commit | Coverage | What it added |
|---|---|---|---|
| geometry | `188ac03` | 11/12 | pack kind `rulekit/geometry@1`: declarative `(shape,quantity)→expr` table |
| list_statistic | `bb9e99d` | 6 ops | per-op sub-categories; consumer reads the question's whole number list |
| number_theory | `bf22837` | 4 ops | per-op sub-categories → `math.gcd`/`lcm`/`factorial`/`comb` |
| arithmetic | `6bdd361` | 7 ops | operator words are grammatical-skeleton literals → ZERO new categories |
| trigonometry | `4ed9956` | 4/4 | one `angle_degrees` gate; two asks (`sine`/`sin`) → ONE opcode |
| coordinate | `720c071` | 3/4 | a `point` slot type: "(3,4)" stops reading as the scalar 34 |
| vector | `7145a89` | 2/2 | whole-list read of a SPACED tuple; forced the `bare:` compound gate |
| unit_conversion | `a241f38`+ | 11/18 | the FIRST typed-gold domain; imperative frame; asks the conversions table |
| physics | (this session) | 3/14 | pack kind `rulekit/formulas@1`: quantity→expr + a unit→DIMENSION map |

`arithmetic` is the lowest-cost variant of the template and the one to imitate: operator words are
skeleton LITERALS in the ask (or the multiplier/percent unit numbers.py already folds), so it needed
zero new categories and only two admitted nouns (`power`, `root`), and its consumer dispatches on a
structural OPCODE (`"add"`/`"multiply"`), never an English word.

Gotchas learned building it (they will bite again):
- `{lit: the}` NEVER matches — the article is an auto-skipped sense.
- "square root" merges into one compound noun; match it as a single `{lit: square root}`.
- The unknown-word guard blocks commit until new nouns are admitted to the lexicon.

Small follow-ups: geometry's right-triangle ("legs 3 and 4"), std-dev / variance / geometric-mean.
**DEFER `probability`** — 8 unrelated formulas is HETEROGENEOUS, a constitution §2 trap.

### `physics` — LANDED at 3/14, and the 11 declines are the interesting part

The addressable pool (measured 2026-07-16): **243 items across 80 domains** (numeric gold, still
declining); 196 sit in domains with ≥3 items. Ranked: physics 14 · chemistry 8 · clock_arithmetic 8 ·
unit_conversion 7 · base_conversion 7 · probability 7 · logistics 7 · optics 6.

**What landed:** pack kind **`rulekit/formulas@1`** — a `dimensions` map (dimension → its ONE canonical
unit) plus `formulas` (quantity → expr over dimension names). The geometry table with the SHAPE
dropped; `answer.py`'s `physics` consumer is the generic evaluator. 3 formulas: speed=distance/time,
weight=mass*9.8 (g lives in the EXPR as data, like `pi`), voltage=resistance*current.

**THE DESIGN CLAIM, and it is the whole increment:** operands bind by the **DIMENSION OF THEIR UNIT**,
never positionally. The unit is the counted unit's LEMMA ("100 meters" → 'meter') **or its QUALIFIER**
when the noun is not a unit ("a 2 kg object" → lemma 'object', qualifier 'kilogram' — the unit survives
ONLY there). Positional binding was rejected because *"an object that took 5 seconds to travel 100
meters"* would confidently answer 0.05 — a rule-4 confident-wrong on unseen text. `test_physics.py`
pins both word orders at 15.0. **Do not "simplify" this to reading the number list in order.**

**Why only 3 of 14, and each reason is a different lesson:**
- **6 items** (force, density, momentum, kinetic energy) need units the tokenizer SHREDS — see the
  phantom-exponent invariant below. Their dimension never binds → `evaluate` NameErrors → decline. The
  decline path IS the guard; no extra code.
- **2 items** (`power`): "What is the power **IF** 100 joules of work is done in 5 seconds?" — the
  leading `if`-clause SPLITS INTO A PREMISE (`engine.split_question`) and `answer()` only receives the
  QUESTION reading, so the operands are not there to bind. The formula and 'joule' were REMOVED rather
  than left as dead weight for something that cannot fire. Reopens if a consumer ever reads premises.
- **1 item** (`work`): 'work' is a VERB in the lexicon, so it cannot join a noun-rooted category (the
  registry rejects it — the `average`/`second` trap). Needs a literal-variant ask, and `work = force *
  distance` needs 'N' as a force unit, which is a single capital the name-merge rule would fight over.
- **2 items** are the PE/KE pair: "kinetic energy" merges to ONE compound noun whose lemma is the head
  'energy', so telling KE from PE needs the qualifier (the `bare:` gate lesson).

**The `_TOKEN` compound-unit change was BUILT, MEASURED and REVERTED — physics stays at 3/14. Do not
re-propose it on its own** (`docs/negative-results.md`, "The `_TOKEN` compound-unit change is SAFE but
UNBUYABLE"). The change WORKS and is byte-neutral on all five word-problem corpora; 51 GSM8K-train
items contain the slashed-pair shape it also fuses ("blondies/brownies") and **zero of them commit**,
so it breaks nothing. It was reverted because **nothing can pay for it** — every formula it unblocks
needs a word with GSM8K **TEST** exposure: force→'force' (1 TEST), kinetic energy→'energy' (2 TEST),
momentum→**'moving'** (1 TEST — the item says "a 4 kg object MOVING at 8 m/s", and the unknown-word
guard checks the whole reading, so no ask can route around it). `density` is blocked by a real
CONTRADICTION the schema caught: its gold needs mass in GRAMS ("3 g/cm³") while `weight`'s needs
KILOGRAMS ("98 N"), and one-canonical-unit-per-dimension rightly forbids both.

The measurement is BANKED: if a future increment ever has an independent reason to admit
'force'/'energy'/'moving' and buys it with a TEST look, the tokenizer change lands with it in one step
and needs no re-litigating. **The lesson: an enabler is not "safe therefore land it".** `_TOKEN` passed
every gate; the reason to revert was that it had no BUYER. Measure the buyer BEFORE building the
enabler.

**⚠ Three confident-wrongs the constitution review caught here, ALL invisible to the difg gate** — the
gate was clean and the review was not, which is the whole argument for the review existing:
1. An **unread count**: "60 meters in 4 seconds and 3 MINUTES" committed 15.0 (true: 0.33). 'minute'
   denominates no dimension, so it bound nothing, was never logged, and value-accounting is EXEMPT for
   this consumer. **Taking the `_WHOLE_LIST_CONSUMERS` exemption means OWNING the accounting** — the
   consumer now declines on any count it cannot read.
2. The **same-value blind spot**: the guard read `env[dim] != value`, so "60 meters then 60 meters"
   committed 15.0 (true: 30) while "60 then 50" declined. Now ANY second value for a dimension
   declines. Same-value collisions defeat accounting guards — the lesson `guards.py`'s Counter exists
   for — and a test written with 60-then-50 passes straight over it.
3. The schema permitted MANY units per dimension while the docstring insisted on one. Now a
   `model_validator` rejects it: a second unit is a second SCALE ("the weight of a 300 g object" →
   2940 N, not 2.94). Prose does not enforce.
4. **BINDABLE is not READ** — the subtlest, and the one to carry forward. "the weight of a 3 kg object
   THAT TRAVELS 60 METERS IN 4 SECONDS" bound distance and time, `mass * 9.8` never referenced them,
   nothing declined, and it committed 29.4 while ignoring two stated quantities. The read set is now
   derived from the EXPRESSION's own names. It was LATENT for these three formulas (travel really is
   irrelevant to weight) and goes LIVE with the `_TOKEN` increment's velocity/acceleration dimensions.
   The log records what was READ, not what was bindable — logging the merely-bindable would launder an
   ignored value into `log.uses_value()`, which other guards consult as evidence.

**And the meta-lesson, which cost two review rounds:** the first fix closed the reported WITNESS
("...and 3 minutes", an unread count) and left the CLASS open — the guard accounts for
count/multiplier/fraction, so "travels HALF of 60 meters" still committed. `_ACCOUNTED_VALUE_KINDS` now
has ONE definition (`answer.py`) that `guards.py` imports, because a contract with two copies has
already drifted. **Fix the class the witness belongs to, and reason from the shared definition, not
from the example you were handed.**

**`clock_arithmetic` (8) is NOT next** despite its size: its golds are TIMES ("12:45 PM", "15:45") =
`text` kind, so they are blocked by the CLOSED kernel lever (Frontier 2). Only 1 of its 8 is numeric.

**`base_conversion` is NOT the next easy domain — it was surveyed and is worth less than it looks.**
Of its 7 DEV items, **2 have POISONED GOLD**: the builder coerced the binary digit-string to a float,
so `Convert 255 to binary` golds as `1.11111e+07` (i.e. `11111100`) — a CORRECT answer of `11111111`
scores WRONG against it (`TOL` is 1e-6 absolute). Those two are unwinnable; never count them as
coverage or chase them. The other 5 also need machinery the template does NOT supply: `Convert
hexadecimal FF to decimal` needs an ALPHANUMERIC literal read as a digit-string (`FF` is not a number
token), and `Convert 1010 from binary to decimal` needs a number token REINTERPRETED in a named base.
That is a real operand-binding increment, not a fifth copy of the template — brief it as such or skip it.

**The trig increment's transferable lesson:** a unit-bearing operand ("30 degrees") folds into ONE
`counted` unit via merge-count, so `{slot: x, type: number}` + `{lit: degrees}` CANNOT match — the
unit token does not survive the merge. Bind one category-gated slot instead. Confirm any new shape
with `rulekit solve --trace` BEFORE writing the ask; the trace prints the merge.

**Tuples: TWO forms, and they are read by two DIFFERENT mechanisms. This is settled — do not redesign it.**
- `(1,2)` **unspaced** is ONE token → `numbers.py` `_TUPLE` → a `point` slot (`720c071`, distance/slope).
- `(1, 2, 3)` **spaced** is THREE tokens (`1,` `2,` `3`, each a plain number) → read as a whole-question
  number list by the `vector` consumer (`7145a89`, magnitude/dot product).

**A merge pass folding spaced tuples into points CANNOT EXIST** — an earlier version of this file
proposed one; that was WRONG. The tokenizer's `_TOKEN` regex has no paren alternative, so parens are
**dropped outright** before annotation: `(1, 2, 3)` and the `list_statistic` list `1, 2, 3` are the
identical token stream. Any such pass would break every statistic list. If a spaced tuple ever needs to
be a real `point`, the ONLY route is teaching `tokenize.py` to preserve parens — a change under every
corpus, almost certainly not worth it.

**`unit_conversion` is 11/18. What is LEFT, and why:**
1. **Temperature (2 items) is AFFINE** — `rulekit/conversions@1` holds a FACTOR only, no offset.
   Needs a schema change for 2 items; probably not worth it.
2. **Digital units (4 items)**: byte/kilobyte/megabyte/gigabyte/terabyte are not in the lexicon at all,
   and "60 miles per hour to kilometers per hour" is a COMPOUND unit (km/h) — a per-unit rate, not a
   member of `measure_unit`.
3. **`second` is an ADJECTIVE in the lexicon** (the ordinal, not the time unit) so it cannot join the
   noun-rooted `measure_unit` category — the registry rejects it outright. Costs 1 item. Do NOT add a
   noun sense: that is the trap that broke the `average` consumer (pytest caught it, not the dev gate).
   A literal-variant ask is the sanctioned fix.

**IMPERATIVES: the mechanism already existed — `imperative` is an ASK_CUE_SENSE (`engine.py`), so a
task sentence with no '?' is a question the moment its verb carries that sense in the LEXICON. Data,
not a kernel change.** `compute`/`calculate`/`determine` already had it; `convert` now does. **50 of
342 difg-DEV items die at "no question found"** and this is how each is unlocked — but ONE WORD AT A
TIME, measured: `convert` opens exactly 2 word-problem sentences, whereas **`find` opens 76 ASDiv-dev,
69 SciBench-dev and 4 GSM8K TEST** sentences, and `evaluate`/`solve` appear only in SciBench (which
must hold 0 commits). Never admit an imperative cue without counting its sentence-initial hits per
corpus first.

**A UNIT SYMBOL needs no new mechanism** — it is a number-form, carried by the ordinary plural map
('kg' was already among kilogram's plurals; 'km' was missing from kilometer's and now mirrors it).
A comment here once claimed symbols needed an abbreviation mechanism of their own; the constitution
review caught that it was WRONG and it was worth +2 items. **Check `plural_to_singular` before
believing a symbol is unreachable.**

**ASK RANKING CHANGED (this session), and it is shared machinery:** `match_ask` ranked ONLY by consumed
units, with **alphabetical id order** as the tie-break — which encodes nothing. "How many inches are in
3 feet?" lost to `ask/how-many-in-place` (which reads "3 feet" as a PLACE and declines) purely because
'h' < 'u'. It now ranks `(consumed units, Σ category-gate depth)`, the same second key
`rule_specificity` has always used for RULES; id order remains the final tie-break. Only TIES are
affected, and all five word-problem corpora measured byte-neutral. If a future ask mysteriously loses,
this is the ranking to read.

**difg reports COVERAGE, NEVER precision** (79.3% of it is difg's own `example_queries`). Never quote
its number beside the GSM8K/ASDiv precision numbers. And note the denominator MOVED this session
(148 → 342 items), so the coverage % is not comparable across that line: 18.2% before vs 9.9% after is
a bigger, more honest denominator, not a regression. See `docs/difg-corpus-plan.md`.

### ✅ DONE: the logic corpus is FOLIO — `projects/folio/` — BUILT, BENCHED, LANDED (`f7b059c`)

**Measured 2026-07-16: 919 DEV / 285 TEST, 0 rows dropped. Baseline `0 correct / 0 wrong`
(919 declined).** Rebuild with `uv run --with datasets python projects/folio/build_corpus.py`.
The DEV label split lands **37.6% True / 32.9% Uncertain / 29.5% False**, so the majority-class
null scores 37.6% — the balance check holds on the ACTUAL built slice, not just the dataset card.

**⚠ IT SHIPPED AT `1 correct / 0 wrong` AND THE 1 WAS LUCK — this is the whole lesson.** The
prediction "expect 0/0, the WRONG column is what matters" was right about the wrong column and
would have MISSED this: the gate's first run scored a `correct`, and a `correct` on a safety gate
reads like good news. It was a guess that landed. **On a safety gate, treat a nonzero `correct`
exactly as seriously as a nonzero `wrong` until you have read the item.** It is now 0/0 because
the bug it exposed is fixed (`b1db917`), not because nothing happened.

**What it caught (the gate paying for itself on its first run, as predicted):**
`ask/is-membership` matches `is <name> <noun>` as a SUBSEQUENCE, so on *"Is it true that Jim is a
**Knicks player**?"* the proper noun QUALIFYING the collection bound the member slot and the real
subject was dropped: member='knicks', 'jim' never read, answered from a Membership fact about the
Knicks. **The null control is what convicts it** — swapping in a name absent from the premises
returned the same 'no', and *"Jim is a Knicks player. Is it true that Jim is a Knicks player?"*
returned **undetermined**. An answer invariant to its own question is not an answer. It scored
`correct` only because that row's gold is False.

The fix took TWO passes, and **the first one was the witness fix** — read this before writing any
guard. Pass 1 (`b1db917`) declined on an unread NAME: value-accounting's *BINDABLE is not READ* for
a kind with no digits (which is why 5 arithmetic corpora sat on it silently — verdicts are not
`Answer.committed`, so each scored it a harmless decline). It shipped with a clean 6-corpus gate, a
null-control test, and a commit claiming it "closes the CLASS". **It did not.** A common-noun
subject has no name to be unread, so `"Is it true that THE PILOT is a Knicks player?"` still
committed `no` about the Knicks — the same confident answer, **one value-kind over**, which is
exactly the failure `fix-the-class-not-the-witness` records. A guard keyed on the witness's value
KIND inherits the witness's blind spot.

Pass 2 (`b5655ca`) fixed the actual defect, which is GRAMMAR: English **fronts the auxiliary** to
ask ("IS Mary a student?" — subject-auxiliary inversion, subject FOLLOWS the copula), and leaves it
in place in an **embedded declarative** ("…that Jim is a Knicks player" — subject PRECEDES it). A
match sequence is contiguous but **FLOATS** (`match_all` retries at every start offset), so the
shape landed on the second construction. New opt-in `at_start` MatchToken flag pins a token to the
front (structure, never lexicon; defaults False so every other rule is byte-identical; an anchor on
a non-first token can never fire, so `AskRule` rejects it at LOAD — a dead rule reads as a clean
0 SOLVED). **The engine had bound `is.subject -> jim` correctly all along — the ask never looked.
A misreading is not always missing information.**

Both are live at different levels and neither subsumes the other: the ask decides WHICH
construction it may read; the guard decides whether the reading used everything the question said
("Is Mary a student AT YALE?" still declines). `undetermined` still survives where nothing is unread.

**No GSM8K TEST look was spent, and that is a PROOF, not an oversight:** the guard only ever turns
a `verdict` into a `decline`, and `_judge` already scored a verdict against a float gold as
`declined` (a verdict is not `Answer.committed`). Both states score `declined`, so every GSM8K TEST
outcome is unchanged by construction. Prefer a proof to a look whenever the change cannot reach a
commit path — looks are the scarcest thing here.

**The scoring path was TRACED through `_judge_typed`, not assumed** (the builder is
unrun, but this part is settled by reading): `#### True`/`#### False` miss
`_NUMBER`/`_MONEY`/`_PERCENT` and hit the `("true","false","yes","no")` test →
`kind='verdict'`; `#### Uncertain` misses `_QUANTITY` (it needs leading digits) →
`kind='text'`. There are **three** routes to a WRONG, all live TODAY with no kernel
change:
1. a committed NUMBER vs a **verdict** gold — fails `got in ("yes","no",...)` → wrong;
2. a committed NUMBER vs the **text** gold — `norm("15.0") != norm("Uncertain")` → wrong;
3. a **verdict** answer vs a True/False gold — hits the boolean comparator and scores
   correct/wrong outright. Verdict asks ALREADY EXIST (difg's is-prime), so an existing
   one misfiring on logic prose is caught immediately. Note this route can score
   CORRECT too — a lucky verdict is a 50/50 coin flip, so treat any nonzero correct
   here as suspect until the item is read, not as coverage.

These premises are full of bindable numbers ("published a book in 1946"), and no
other corpus can see route 1 or 2 — all five others ask for a number.

**The four checks, all MEASURED before wiring** (full table + the ProofWriter
rejection: `docs/negative-results.md` → "The logic-corpus search"). Do not re-derive:

| check | FOLIO | verdict |
|---|---|---|
| independent authors | Yale-LILY, human-written (arxiv:2209.00840) | pass |
| **balanced labels** | True 38.8% / Uncertain 32.4% / False 28.9% → **null = 38.8%** | pass |
| natural English | 1,662 skeletons / 5,286 premise sentences; top = **0.2%** | pass |
| verifiable golds | premises-FOL + conclusion-FOL on 100% of rows | pass, caveated |

- **ProofWriter/RuleTaker REJECTED** on natural English, and it is not close:
  292,776 questions drawn from a **52-word vocabulary** ("Gary is furry", "Bob is
  not blue"). Size is not independence — 292K rows of a generator carry less
  information than 1K rows of human prose. LogiQA/ReClor unmeasured: MCQ golds are
  option labels, so the shape is wrong regardless of the text.
- **The FOL is NOT an executable oracle** — 3.2% of `conclusion-FOL` strings do not
  have balanced parens. It is human annotation, carried for AUDITING a
  disagreement; the gold is FOLIO's human-verified label. The dataset card cannot
  tell you this; testing it can.

**⚠ WHAT FOLIO ACTUALLY BUYS — Frontier 2 is reopened, but it is NOT a
`Answer.committed` widening.** The old brief implied the corpus was the only
missing piece. It was not. Widening `committed` to admit verdicts buys nothing on
its own, because **there is no inference engine behind it** — FOLIO needs universal
quantification, implication chaining, negation and XOR over human prose. Worse,
`engine.split_question` splits a leading premise off and `answer()` only receives
the QUESTION reading (the physics `power` lesson), so **the premises never reach the
consumer at all**. Mining FOLIO means building a premise-reading consumer AND an
inference engine. That is a frontier, not an increment. Brief it honestly or the
first candidate against it will be a dead brief.

**Two traps caught before landing (both in `negative-results.md`):**
1. **'Uncertain' is a `text` gold, NEVER a `decline` gold.** `_judge_typed` scores a
   declining engine `correct` against a decline gold — so that mapping would hand an
   always-decline engine ~32% of this corpus for zero reasoning. That is difg's
   always-yes disease reappearing **in the corpus chosen to escape it**: the null
   control must be re-run on every design decision, not just on corpus selection.
2. **The firewall buckets on the PREMISE BLOCK, not the item.** 1,001 rows share only
   **340 stories**; asdiv's per-item hash would have leaked **661 of 1,001** across
   the cut. The "two-file recipe" hid this — copying the builder verbatim was wrong.

**The old brief (kept — the reasoning below is still the standard for a 7th gate):**

**Why difg's own logic cannot be that buyer — measured 2026-07-16, do not re-derive:**
- difg's entire logic domain is **10 `example_queries`** in a 64-line orchestrator
  (`~/Development/experiments/difg/reasoning/store/orchestrators/logic.py`). **9 of
  the 10 are ALREADY in `projects/difg/`** (5 DEV, 4 TEST); the 10th ("Construct
  the truth table for P AND Q") has no extractable gold. There is nothing to import.
- **All 8 prose yes/no golds in difg-DEV answer 'Yes'.** Not one 'No'. So an engine
  that answers 'yes' unconditionally scores 8/8 — the null scores as well as the
  real thing and the measurement carries NO information ([[measure-with-a-null-control]]).
- That is not sampling luck. The orchestrator's own phrase table proves difg CAN
  say no — `"tautology": ("Yes, it is a tautology.", "No, it is not a tautology.")`
  — **its corpus just never asks.** `example_queries` are DEMOS: the questions difg
  published because its answer was yes. This is the 79.3%-self-portrait finding
  (docs/difg-corpus-plan.md) surfacing as a degenerate label distribution.

**What a usable corpus must have — all four, and check them BEFORE wiring:**
1. **Independent authors.** Not difg's, not generated by us. The whole point is a
   gate that sees what our corpora structurally cannot.
2. **BALANCED labels.** Count them first. If it is >80% one label, an always-that
   engine scores well and it is another degenerate gate — walk away.
3. **Natural English.** MAWPS is the cautionary tale, measured this session: 84% of
   its pool is ONE auto-generated template with substituted nouns ('some Beg') and
   broken grammar ("Now How many fig Joseph have minus?"). It commits 9 of 2007.
   Fitting a rule to that measures the generator, not reading.
4. **Verifiable golds.** Propositional logic is the rare domain where the gold is
   mechanically checkable (truth tables), so a disagreement is a real bug rather
   than a judgement call.

**Candidates to evaluate** (not yet looked at — this is the task): **FOLIO**
(natural-language first-order logic, human-written, balanced true/false/unknown —
the most promising on paper), **ProofWriter** / **RuleTaker** (rule-based
entailment; check for template-ese, they may fail #3), **LogiQA** / **ReClor**
(multiple-choice reading comprehension — probably the WRONG shape: MCQ answers are
option labels, not verdicts). Prefer HF-backed so `build_corpus.py` mirrors the
existing four.

**⚠ DO NOT generate our own logic corpus.** It was considered and rejected: the
golds would be trustworthy (truth tables are objective) but it would be one
template × substitutions — our own MAWPS. Scoring well on it measures our
generator. If no third-party corpus survives the four checks above, the honest
outcome is that logic STAYS CLOSED; record that and move on.

**If a corpus passes, the kernel work it buys — read these first, they are traps:**
- `Answer.committed == (kind == "number")` is the blocker. Widening it MUST keep
  excluding the verdict **'undetermined'** — that is the epistemic square's "I
  don't know", and if it counts as a commitment every honest decline becomes a wrong.
- **`_judge_typed`'s verdict rule must be revisited IN THE SAME INCREMENT** (it is
  flagged in-code at `harness/bench.py`). "A verdict against a non-verdict gold is
  a decline" holds ONLY while verdicts are non-commitments; once they commit, that
  line HIDES real confident-wrongs.
- The asymmetry beside it is already correct and must stay: a committed NUMBER
  against a text/set gold IS a wrong — the engine asserted an answer of the wrong shape.
- difg's own prose golds ("Yes, 17 is prime.") will still score a correct `yes` as
  WRONG on exact-compare. A new corpus with bare True/False golds sidesteps this;
  do not "fix" difg's prose golds to make them pass.

**Where the machinery already is:** `TypedGold` + `_judge_typed` (harness/firewall.py,
harness/bench.py) handle verdict golds today — `gold: typed` is landed and difg
declares it. The comparator compares verdicts as BOOLEANS, not strings. So a new
corpus needs `build_corpus.py` + `project.yaml` and probably NO harness change.

### FRONTIER 2: TYPED GOLD — corpus half LANDED; the KERNEL half is CLOSED (measured, not skipped)

**What landed** (`a241f38`). difg declares `gold: typed`; its builder keeps every typed gold verbatim
and the loader classifies the payload STRUCTURALLY (`firewall.parse_typed_gold`) instead of dropping
it. difg-DEV **148 → 342 items** (TEST 49 → 107, reserved). Firewall re-verified on the rebuild: 0
pre-existing items missing, 0 golds changed, **0 dev/test crossings** (bucket = `md5(SALT + question)`,
per-question). `gold` defaults absent = today's float path, so no other corpus can reach the typed
branch.

**The kernel half is CLOSED — do NOT widen `Answer.committed` for difg's sake.** Full evidence in
`docs/negative-results.md` → "The typed-gold KERNEL change is NOT the big lever". The short version,
measured over all 342 DEV golds:

| gold kind | count | scorable today? |
|---|---|---|
| number 145 · quantity 108 · money 21 · percent 10 | **284 (83%)** | **yes — none needed the kernel change** |
| verdict (bare) | 2 | no |
| text | 56 | no |

- The plan's **"55.5% non-numeric" headline counted quantity+unit (29.5%)** — but a quantity gold is a
  NUMBER under a formatting wrapper ("68.04 kg") and `_judge_typed` compares it numerically.
  `Answer.committed` was never its blocker. The two halves were conflated; the smaller was mistaken
  for the lever.
- The change would buy **~10 items (2.9%)** and would **manufacture confident-wrongs**: `Is 17 a prime
  number?` golds as the SENTENCE `'Yes, 17 is prime.'`, so a committed (correct!) `yes` scores WRONG.
- And the prose-verdict comparator that would fix that **must not be built either**: **8 of 8** prose
  yes/no golds in DEV answer **'Yes'** — an always-yes engine scores 8/8. The null scores as well as
  the real thing, so the measurement carries no information (the null-control lesson).
- The other **43 text items are a different engine**: integrals, Taylor series, power sets, topology,
  quaternions, Cantor normal form. SymPy answers; no rule pack reaches them.

**If the kernel ever grows a non-numeric commit path for some OTHER reason, read `_judge_typed`'s
in-code ⚠ first:** its "a verdict against a non-verdict gold is a decline" rule is correct ONLY while
verdicts are non-commitments, and would hide real wrongs the day they commit.

---

## The corpora (five cross-corpus gates)

Run on ANY kernel/pack change (methodology §3b, lifecycle step 6b). Each is a `project.yaml` + a
committed salt-split `build_corpus.py`; data gitignored; flows through the existing harness with zero
new code. **Adding one is a two-file recipe.**

| Project | Role | Baseline |
|---|---|---|
| `projects/gsm8k/` | the mined corpus; now a regression floor | 104/0 dev-train, TEST 92.3% |
| `projects/asdiv/` | different authors, same task | **100%** (43/0) |
| `projects/svamp/` | **adversarial variations**, harshest in-domain | **100%** (13/0) — self-comparison guard `2b8430b` |
| `projects/mawps/` | classic arithmetic repo | **100%** (9/0), low coverage |
| `projects/scibench/` | **out-of-domain** college science; safety check | **0/0** — a rising wrong = the engine guessing |
| `projects/difg/` | multi-domain COVERAGE corpus (not precision); `gold: typed` | 44/0 of **342**, 9 domains |
| `projects/folio/` | **LOGIC** safety gate (6th); `gold: typed`; the only NON-arithmetic gate | **0/0** of 919 — caught the unread-name verdict on run #1 |

The four HF-backed ones rebuild with `uv run --with datasets python projects/<name>/build_corpus.py`;
difg reads a LOCAL difg checkout (`uv run python projects/difg/build_corpus.py`, no `--with datasets`).

The gate discipline paid off — every kernel fix last session was BOUGHT by these corpora, not by
GSM8K: distributive-container guard (`5537d10`) · value-accounting multiplicity (`b49659e`) ·
synth-GroupTotal fix + consumer both paths (`2439b82`, `ab878ad`) · container+loose composition
(`6dffe56`) · subject-gapping anaphora (`22623ee`, GSM8K TEST 91.7%→92.3%) · superordinate-via-combined
(`1466051`, "pieces of litter").

## Current numbers (re-measured at `b1db917`, 2026-07-16 — every one of these was run, not carried over)

- GSM8K dev-train **104/0** · dev-holdout **40/0** · TEST **92.3%** (12/1, unchanged — no look spent
  this session; see the proof under the FOLIO section) · curated suite **52/52**
- pytest **1209** · lint: 0 errors, 1 intended warning (fraction-of-remnant subsumption — documentation, not a bug)
- Cross-corpus DEV: **ASDiv 100% (43/0)** · **SVAMP 100% (13/0)** · MAWPS 100% (9/0) · SciBench 0/0 ·
  difg 44/0 of 342 (typed gold) · **folio 0/0 of 919** (typed gold)
- bench wall: dev-train 16.6s → 9.0s (trace opt-out) → 1.7s at `--jobs 12`. `--jobs` defaults to 1;
  spend it in the SERIAL integration tail, never in the implementers' gates (they already run concurrently).

## The mining loop (how work ships)

1. Baselines live in `projects/gsm8k/snapshots/` — `conj-train.json` / `conj-holdout.json` supersede
   `price-*` / `pop-*` / `conv-*` / `narrow2-*`. **They are NOT "identical to head behavior"** (this
   file claimed that; measured 2026-07-16 it is false): `conj-train.json` is the original ~14-correct
   baseline and reads **90 SOLVED / 0 BROKE** against head's 104/0. Still a valid FLOOR — 0 BROKE and
   0 DECL→WRONG mean exactly what they say — but `NET` against it is meaningless. For a real
   before/after, snapshot the PRIOR COMMIT. `--snapshot` now works on typed-gold projects (`d0a818e`).
2. Mine with throwaway scripts in the session scratchpad (never the repo); `rulekit stats` also works.
3. Build the tightest GENERAL mechanism (YAML rules/categories first; kernel only for structure).
   One class per increment, named at ship time.
4. Gate: `bench --slice dev-train --snapshot X.json` → `diff <baseline> X.json` (must be **0 BROKE /
   0 DECL→WRONG**) → same for dev-holdout → synthetic pytest (never GSM8K strings) → curated suite holds 65/65
   → the five cross-corpus gates.
5. TEST look per shipped increment: `bench --slice test --spend-test-look`. Precision must hold vs the
   last look or the increment REVERTS.

Batch alternative: `/mine [count]` runs steps 2–4 as a multi-agent pipeline (scout → parallel Sonnet
juniors in isolated worktrees → constitution review → sequential landing onto `mining/batch-<date>`
with a full re-gate per increment). It never touches TEST or main: step 5 stays manual, one look per
landed increment walking the staging commits in order; fast-forward main past survivors only.
See `.claude/skills/mine/SKILL.md`. **Standing instruction: push `main` after every processed batch.**

## Hard-won invariants (do not relearn these)

**Gates and accounting**
- **GATE HAZARD** (`a833fea`): a stash-based before/after gate is UNSOUND when an increment adds NEW
  pack files — `git stash push -- <files>` does not revert UNTRACKED files, so the "before" baseline is
  contaminated and a real regression reads NEUTRAL. This masked a 104→103 GSM8K drop. When an increment
  adds files, `git add -A` first, or check out the prior commit to snapshot.
- **An increment you cannot revert independently is not an increment.** Every TEST look buys the right
  to revert exactly one thing; two unrelated changes in one commit destroy that, and the whole firewall
  rests on it. (Increment 107 — a `yaml_only` brief that also rewrote three `numbers.py` merge passes.)
- Every new FACT KIND must decide explicitly whether existence or USE constitutes "read" for value
  accounting (the look #4–#7 lesson).
- **VALUE-ACCOUNTING IS NUMERIC, so every NON-numeric value a consumer binds needs its own read
  guard.** A dropped NAME carries no digits, so no numeric guard can see it: `membership-verdict`
  bound a collection's proper-noun qualifier as its subject, ignored the real one, and answered
  anyway (`b1db917`). Five arithmetic corpora sat on it silently because verdicts are not
  `Answer.committed`. Ask of any consumer: *which kinds does it BIND, and which of those can go
  unread without a guard noticing?*
- **A GUARD KEYED ON THE WITNESS'S VALUE KIND INHERITS THE WITNESS'S BLIND SPOT.** The guard above
  keyed on an unread NAME and sailed past the same confident answer with a common-noun subject —
  one kind over, gate clean, commit message claiming it "closes the class" (`b5655ca` is the real
  fix). Before writing a guard, ask *what is this witness an INSTANCE of, and what else fits that
  position?* — one probe, cheaper than the gate and tests that follow.
- **"CHARACTERIZED" IS NOT "MEASURED" — re-read a tail before believing it.** This file called the
  7 remaining confident-wrongs "the hard tail"; reading them found a 2-item mechanical class fixable
  by ONE condition, worth SVAMP going to 100% precision, plus an UNWINNABLE poisoned gold nobody
  should ever chase. Four inherited claims failed on contact this session (untracked files, a stale
  baseline, a crashed ship gate, this). A worklist description is a memory of someone else's
  session; the read is cheap.
- **A MIS-BINDING IS INVISIBLE TO EVERY NUMERIC GUARD** — the arithmetic is impeccable *given* the
  wrong binding. Three of this session's bugs are this one shape: `|josh - josh|` (both ask slots
  resolved to one person), the membership subject ('Knicks' bound instead of 'Jim'), and the
  transfer whose two legs move different amounts. Value-accounting checks that digits were READ, not
  that they were read as the RIGHT thing. When a consumer binds two things, ask what happens when
  they collapse onto one.
- **A PLAUSIBLE ARITHMETIC STORY IS NOT A DIAGNOSIS — DUMP THE FACT STORE.** "17 vs 16.5" was
  briefed as a transfer whose legs disagree (giver −9, receiver +8.5). Neither number existed: the
  store had ONE leg of 17.5 (half of the POOLED 35) and no receive leg. Inferring a mechanism from
  the output number reconstructs *a* story that produces it, not *the* one. `solve()` + printing
  `store.facts` is one script.
- **THE CORPUS GATE CANNOT SEE A CONTRACT NO CORPUS PHRASES.** A holder-count fraction guard passed
  ALL SIX corpora (ASDiv even improved) and was still wrong: it broke "Tom ate half of THE eggs"
  (= 11, the DEFINITE pool legitimately spans entities), caught only by a unit test whose NAME states
  the contract — `test_fraction_pool_spans_entities`. Before changing shared kernel behavior, GREP
  THE TESTS for the behavior you are about to change; "all gates green" is not a verdict.
- **A MATCH SEQUENCE FLOATS: `match_all` retries at every start offset**, so a shape mined on one
  construction lands on any later one containing the same token run. `is <name> <noun>` was written
  for the FRONTED interrogative ("IS Mary a student?" — the subject follows the copula) and drifted
  onto the EMBEDDED DECLARATIVE ("…that Jim is a Knicks player" — the subject precedes it), binding
  the complement's name-modifier as the subject. Opt-in `at_start` (schemas.MatchToken) pins a token
  to the front. **When a shape misfires, suspect the CONSTRUCTION before the guard** — and note
  `_try_match_at` itself is contiguous; only `match_all` floats.
- **On a SAFETY gate (scibench/folio), a nonzero `correct` is as suspicious as a nonzero `wrong`** —
  and it is harder to act on because it looks like progress. FOLIO's first run scored 1 correct: a
  verdict invariant to its own question that drew the ~39% of the label distribution which hides a
  guess. Read the item before calling it coverage. **A guess and a capability are indistinguishable
  at n=1** — the null control (swap the subject for one the premises never mention; does the answer
  move?) is what tells them apart.
- A new derived-total consumer must check for UNCONSUMED QUALITATIVE predicates on the same entity
  before committing, not just unaccounted NUMBERS — value-accounting only catches missing digits;
  "splits the cost with his brother" has none and slipped past every numeric guard.
- **Prose does not enforce.** A rule that keeps being broken needs a MECHANISM, not a comment — the
  DEAD_CLASSES map in `mine.js` exists because a prose stop-rule was ignored the very next batch.
  A class leaves that list when its blockers LAND, never because a scout feels differently.

**Blast radius**
- A shared clause-boundary scan (`_is_rate` / `_price_each_value`, used by EVERY verb's rate-marker
  detection) must never be widened globally to fix one caller — the fix is an opt-in parameter,
  defaulted to old behavior. Any tightening of a shared scan needs a FULL dev diff.
- **A COMPOUND UNIT's EXPONENT is a PHANTOM OPERAND.** `tokenize.py`'s `_TOKEN` has no compound-unit
  alternative, so "3 m/s^2" tokenizes as `3` … `2` and "100 cm^3" as `100` … `3` — the exponent
  becomes a free-standing number. Any consumer that reads the question's whole number list
  (`list-statistic`, `vector`, and anything copying them) will bind it as an operand. Harmless today
  only because no ask reaches those items; it is the first thing physics must fix.
- **`numbers.py` `_DIGIT` is the number reader for EVERY corpus, not "the parser for the thing you are
  fixing."** Tightening it to reject "3,4" (a coordinate misread as 34) also silently dropped its
  ACCIDENTAL tolerance of a trailing comma — and in a spaced list the tokenizer keeps the comma on the
  fold ("12,"), so three unrelated `list_statistic` items BROKE (`720c071`, caught as 3 SOLVED / 3
  BROKE = REVERT). The pattern's incidental behaviors ARE its contract. Both directions are now pinned
  in `tests/test_coordinate.py`; keep them there.
- A widened slot TYPE (e.g. `entity` vs `name`) must be applied to the SPECIFIC ask/rule ids that need
  it, never via blanket find-replace — most `who: name` slots are intentionally name-only. (Caught with
  `replace_all` during the population re-land.)
- **A COMPOUND NOUN KEEPS ITS HEAD'S LEMMA, and a `cat:` gate matches on lemma** — so a category-gated
  slot cannot tell "the dot product" from "the product" (it committed 720 for a dot product the moment
  'dot' was admitted). `bare: true` on a slot (`7145a89`) demands the head itself. It is OPT-IN and must
  stay that way: for most categories a compound IS its head (a chocolate cake is a cake, and every
  entity/superordinate gate rests on that). Set it ONLY on operation-naming slots, where the head is a
  false friend. Any admission of a modifier that can precede an operation name ("cross", "scalar", "inner")
  re-opens this — the gate is now the mechanism, not a note.

**Reading / grammar**
- Polarity, stateness, and plurality are DATA (categories: acquire/lose ±1, state, produce/receive +1;
  lexicon `number:` field). An untagged event verb declines the fold — tag it in difg-mined members,
  never default +1.
- All state verbs (have/own/be) are ONE equivalence class for relation-resolution blocking; relations
  carry the sentence's verb.
- Fractions/rest resolve strictly in sentence order (out-of-order = self-collision); pools = signed sum
  of prior-sentence facts, synth/rest excluded.
- Name merging: only single capitalized WORDS join names; merged units never do. (Watch collisions:
  'max'/'min' vs the name "Max" silently cost a GSM8K item — `a833fea`.)
- **Admitting a word REMOVES a decline guard** — its blast radius is a confident-wrong, so every
  admission needs a collision grep across ALL corpora FIRST. `4ed9956` withheld 'tan' (a surname in
  GSM8K TEST, a verb in train) and 'cos' (LaTeX in SciBench) on exactly this basis; the class was
  fully served without them. Withholding a colliding word costs nothing when no ask needs it.
  `720c071` withheld 'line' the same way and PAID one difg item for it — the right trade: one item on
  a COVERAGE corpus is never worth risking GSM8K TEST at 92.3%. Check the plural map before admitting
  a plural: 'points' already resolved via points→point, and a redundant second identity is the bug
  that broke 'average'.
- Asks match by specificity (max consumed units); ask templates referencing unbound optional slots omit
  the key; only `{slot.value}` slots count as consumed.
- The verb→dobj binding captures only the FIRST conjunct in "buys X and Y" for verbs outside
  `purchase`/`state`. Closed for purchase verbs (inc. 11) and state verbs (inc. 35); **STILL OPEN** for
  'contains' and event verbs generally.
- `check packs/difg-mined/quarantine.yaml` before admitting new vocabulary (holdout poison; 'fruit' is
  quarantined after it cost a TEST look).
- The 'world' entity (bare existentials) and `measure: currency` are pack-owned data constants.

**Briefing**
- **An ask shape without its premise machinery is a DEAD BRIEF.** A candidate must brief BOTH halves:
  (1) the ask shape, AND (2) the premise mechanism deriving the quantity it folds. A brief naming only
  (1) passes a naive frequency check and fails the shape gate — that is the gate being CORRECT.
- **0 SOLVED is a warning, not a neutral fact.** An enabler must be bought; two infra increments passed
  a clean dev gate and shipped wrongs to TEST.
- Latent bugs come from candidates that FAIL, not from coverage mining. Four were found that way last
  campaign: weekday names (88), stale relation anchor (99), coordinated-clause binding (101),
  number-merge fixpoint (107).

## Closed — do NOT restart

All recorded in `docs/negative-results.md`:
- ask-shape mining (5 batches, +2 net) · the 481-item per-unit seam (mechanism exists) · composition
  (`docs/composition.md`, abandoned Phase 0, typed ceiling ~13) · the reading gap (long tail)
- **the typed-gold KERNEL change** (2026-07-16) — buys ~10 of 342 difg items and manufactures
  confident-wrongs doing it; the prose yes/no golds it would unlock are **8 of 8 'Yes'**, so the
  measurement cannot tell a working engine from an always-yes one. The corpus half was the whole
  prize and it LANDED. Frontier 2 above has the table.
- **the month/time seam** — 220 dev-train items mention a month or weekday; all 220 decline. Relaxing
  the mixed-time refusal measures **0 SOLVED, 0 BROKE**. They need real temporal arithmetic.
- **the 502-item `no 'X' events known` bucket is NOT a class** — it is the hard multi-step tail
  (overtime tiers, multi-leg commutes, itemised purchases). Never brief it as one class.
- the GroupTotal consumer fix (now LANDED, both paths)
- the partitive-entity ask (REVERTED — reintroduces confident-wrongs on event-laden problems; the ROOT
  was subject-gapping, since fixed)

## TEST ledger (125 looks spent)

The live ledger is `projects/gsm8k/snapshots/test-ledger.jsonl` (gitignored — this file and the archive
are the only committed record). The walk, condensed:

`0/1 → 4/1 (80%) → 5/1 (83.3%) → 6/1 (85.7%, look #11 — first genuine coverage gain) → 7/1 (87.5%,
#56) → 8/1 (88.9%, #64) → 11/1 (91.7%) → 12/1 (92.3%, current floor; re-confirmed at look #125,
the 'plants' sense fix — the only look this session, and the only one of six precision fixes that
could not be proven TEST-neutral by construction)`

Three reverts, all caught by the firewall, all documented in `docs/negative-results.md`:
- **look #20** — the 12-word vocab batch, 6/2. Reverted; culprit later identified as `fruit`.
- **look #32** — the fruit/fruits family alone, 6/2. Reverted; `fruit` now quarantined.
- **the rate-machinery revert** — fully re-landed look-by-look (#5–#9). The culprit was
  accounting-by-existence, not the mechanisms; all four pieces are LIVE.

The 1 persistent TEST wrong is a stable §3a unseen shape, present since look #1.

## Quick commands

```
uv run pytest -q
uv run rulekit --project projects/curated bench --slice suite
uv run rulekit --project projects/gsm8k bench --slice dev-train|dev-holdout [--snapshot F]
uv run rulekit --project projects/gsm8k diff conj-train.json <new>.json      # ship gate
uv run rulekit --project projects/gsm8k stats                                # mining worklists
uv run rulekit --project projects/gsm8k serve                                # designer :8321
uv run rulekit --project projects/<asdiv|svamp|mawps|scibench|difg> bench --slice dev --jobs 8
uv run rulekit --project projects/gsm8k bench --slice test --spend-test-look # DELIBERATE
```

Auto-memory (`~/.claude/projects/-Users-louis-Development-rulekit/memory/`) carries the same state in
condensed form and loads automatically.

## History

The full 6,107-line per-increment log of the GSM8K campaign (increments 10–128, batches 1–52, the
goal run 39 → 100, the deixis seam, the retarget) is archived verbatim in
**`docs/HANDOFF-archive-2026-07-16.md`**. Every increment there names its commit, so `git log` and
`git show <sha>` are usually the faster route. Nothing was deleted — this file is the index; the
archive is the record.
