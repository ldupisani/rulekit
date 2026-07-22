# The breadth-first premise-reader campaign — FOLIO logic → full integration

**ACTIVE. Phase A and Phase B readers 1–38 completed through 2026-07-22: ground
both-or-neither equivalence, unrestricted bare-plural disjunction, and negative
two-article indefinite generics, plus single-antecedent verbal “Everyone who”
implications, verbal-restrictor conditionals, and the negative-antecedent
same-entity ground conditional, plural-generic `people` conditionals, and
class-scoped bare-plural copular relatives, restricted `Everyone … is
[either] … or …` disjunctions, and two-article indefinite-generic exclusive
disjunctions, plus negative possessive universals, plural-agreeing negative
event universals, named ground do-support event denials, bare-plural
future-event exclusive disjunctions, and future-negative indefinite
generics, named mixed possession/event disjunctions, and singular positive
possessive universals, plural-generic copular-to-verbal conditionals,
indefinite-generic verbal conditionals, reduced-relative people universals,
fully repeated ground both-or-neither equivalences, implicit-restrictor
property universals, second-person generic conditionals, grammar-proven
fused premise/question boundaries, active participial-restrictor possessive
universals, plural-agreeing positive possessive universals, comma-bound
free-relative verbal conditionals, indefinite-generic inclusive disjunctions,
participial compound verbal universals, named-PP existentials, direct passive
named agents, PP-restricted negative universals, reversed named memberships,
exactly-three named distributive copular subjects, and reversed definite role
memberships, exactly-four asyndetic named copular lists, past indefinite
existentials with definite PP descriptions, and definite-description ground
copular memberships.**

## Context

The benchmark-loaded FOLIO logic frontier lives in `projects/scratch/`: no benchmark project
loads `projects/scratch/packs/logic`, and the real `projects/folio` remains the repo's sole
expect-0-commits safety gate. Some supporting consumers and saturation plugins already live
in the shared kernel, dormant unless pack rules make them reachable; Phase A therefore
inventories that shared machinery rather than treating Phase D as merely a pack move. Five
TEST looks are spent. Looks #3–#5 returned identical aggregates
(1 correct / 1 wrong / 283 declined of 285, precision 0.5 held), and looks #4–#5 measured
**zero transfer** from ~19 dev-train conversions across 8+ distinct stories — including three
designed inference stages (elimination, reductio, identity). The recorded diagnosis
(`projects/scratch/ROADMAP.md` look-#5 entry; `folio-campaign-state` memory): a TEST
conversion requires an entire story STACK (every premise reader + inference shape + ask) to
align, and at 285 TEST items the overlap with any 20-story dev sample is ~0. Story-by-story
mining cannot move TEST. The sanctioned route to integration is **breadth-first
premise-reader coverage of the convertible pool's common blocker classes** — a different
campaign with a different cost curve. This file is that campaign's plan.

## Fixed facts the plan is built on (do not re-derive)

- **Historical Stage-9c convertible pool = 314** dev-train declines (137 false-gold +
  177 true-gold). Phase A resolved the current number: nine later conversions leave
  **305 raw / 302 actionable** verdict-gold declines. The 169 'Uncertain' items are
  `text` golds — never convertible, wrong-hazards only. See the Phase A record at the
  end of `projects/scratch/ROADMAP.md` and `folio-blocker-baseline.json`.
- Post-Stage-7 split: 301 no-ask declines vs 179 consumer-reached undetermined; 76
  "near-frontier" declines (conclusion side reads, no logic fact decides).
- Stage-6 gap taxonomy (over the then-170 undetermined; STALE, re-measure in Phase A):
  entity-atoms-unrelated 52 · entity-raw-other 37 · paraphrase-gap 28 · entity-in-raw-or 23 ·
  entity-absent 13 · entity-in-raw-if 10 · substring-bridge 2.
- Banked zeros (rebuild only WITH a measured buyer): `_naive_singular` -se/-ce/-ze fix,
  CamelCase-name senses, verbal universal conclusion asks. Re-measure after reader changes
  (the 8d lesson: a zero is scoped to its join).
- Unwinnable, never chase: Dickinson [7]/[8]/[9] (missing-period mega-sentence), item 228
  (FOL-verified poisoned gold), [99] (event/time machinery).
- The one real TEST hazard: indefinite subjects — the `blocks_skipped: indefinite_article`
  gate is BUILT (Stage 5 precondition 1). Preconditions 2–3 (ladder re-measure with null
  controls; looks only at class-sized commit counts) still bind.
- Measurement harness: no scratch datasets — folio-with-logic is measured by temporarily
  wiring `./packs/logic` into the folio project (never committed), `rulekit --project
  projects/folio bench --slice dev-train|dev-holdout --snapshot` + `diff`
  (`src/rulekit/cli.py:72,107-114,276-306`). Snapshots in `projects/folio/snapshots/`.
  Firewall: `build_corpus.py` buckets by PREMISE BLOCK, `SALT = "folio-test@1"` — never touch.
- Existing machinery (`projects/scratch/packs/logic/`): ~70 rules in `rules/logic.yaml`
  (copular/bare-plural/verbal universals, conditionals, disjunctions, enumeration, alias,
  appointive passive, ~14 ask shapes), 16 synths in `synth.yaml` (instantiation, chains,
  MT, DS, XOR, case analysis) + 3 saturate plugins (elimination, name-prefix-alias,
  name-head-sortal) + the reductio engine in `consumers/logic_verdict.py`.

## Campaign phases

### Phase A — re-survey the pool by BLOCKER CLASS — DONE (2026-07-20)

Goal: replace the stale Stage-6 taxonomy with a current, per-PREMISE classification of the
current pool, ranked by expected stack-readiness gain / estimated reader cost, scoped to
verdict-gold items only. A large expensive class does not rank higher merely because its cost
is larger.

1. Scratchpad classifier (throwaway, per `docs/methodology.md` §4 — never committed):
   for every item in the pool, dump the fact store + fragment-veto reasons per premise
   sentence; bucket premises by construction (passive, relative clause, do-support negation,
   compound generic, scope-ambiguous "All X are not Y", unknown vocabulary, coordination,
   definite description/anaphora, modal, temporal). Labels are MULTI-LABEL: a premise may
   carry several blockers, and class totals therefore need not sum to the premise count. A
   separately recorded primary blocker may be used for ordering, but its precedence must be
   declared rather than inherited from classifier branch order.
2. **Optional oracle (pydelphin/ACE+ERG, offline only):** run the ERG over the pool's
   premise sentences to label constructions mechanically (passive/relative/scope/unknown
   word). Strictly a survey tool in the scratchpad — never a runtime dependency, never in
   the verdict path. Skip if setup costs more than a session; hand-classification of veto
   reasons is the fallback.
3. The classifier may be throwaway; the evidence defining a long-running gate may not be.
   Deliverables committed to `projects/scratch/`: a refreshed taxonomy table in ROADMAP.md,
   the resolved 311-vs-314 number, exact label/precedence definitions, corpus + registry
   fingerprints, counts by dev-train/dev-holdout and story, and a machine-readable DEV-only
   baseline report containing IDs/labels but no copied TEST data. Record enough regeneration
   detail that a later session can reproduce the totals without relying on memory.
4. Record three nested baselines, not one soft proxy:
   - **fact-bearing**: premise mints at least one fact (diagnostic only; insufficient alone);
   - **fully read**: no operative span remains under a fragment veto or unknown-word block;
   - **stack-ready**: the ask and conclusion are represented, every required premise is fully
     read, at least one fact-key path overlaps the conclusion's entities/predicates, and the
     story has no new contradiction, quarantine, or ambiguous-alternative state.
5. Inventory the already-shared kernel consumers/plugins reached by the scratch logic pack.
   Promotion risk is the change in reachability of shared machinery, not just moving YAML.
6. Phase A closes by pre-registering numeric Phase C thresholds for BOTH grouped DEV splits
   and publishing the Phase B build order by expected stack-ready gain / cost.

Resolution: the baseline is 43.72% / 45.01% fully read and 11 / 5 stack-ready stories
(dev-train / dev-holdout). Look #6 requires at least 51.73% / 53.06% fully read,
truth-scope-veto premises at most 499 / 460, stack-ready stories at least 22 / 10, three
served construction classes, and no hazard increase. The measured first reader is
`entity-in-raw-or` (conjunctive disjuncts); do-support negation is demoted because its
marginal stack estimate is zero on both splits. Exact definitions, counts, fingerprints,
and the remaining build order are recorded in `projects/scratch/ROADMAP.md`.

### Phase B — premise readers by class, breadth-first (the long middle)

Goal: raise READING coverage across the pool, class by class — not conversions per story.
The measured lever is the veto-lift (four precedents: 8g, 9d ×2, 9f): a read sentence stops
pricing its item, independent of whether that item converts.

Rules of engagement (all inherited, non-negotiable):
- One class = one increment = one revertible commit, landed in `projects/scratch/packs/logic`.
  Full gate per increment: pytest (synthetic only), all nine benchmark slices snapshot-diff
  NEUTRAL, folio-with-logic dev-train + dev-holdout diff (0 BROKE, 0 DECL→WRONG), null
  controls on every conversion. Whole-construction-or-nothing matching; unread stays
  monotone-safe.
- Track THREE metrics per increment: conversions (may be 0 — acceptable for readers),
  fully-read/veto movement for the targeted class, and stack-ready story movement. Merely
  minting any fact is not buying: the intended blocker must disappear and the emitted key
  must be relevant to an existing conclusion/inference join. An increment that moves none is
  an unbought enabler — revert and bank it (the `enabler-must-be-bought` memory, relaxed ONLY
  in that measured reader or stack movement now counts as buying).
- Every reader increment gets falsification tests even when it converts zero corpus items:
  a synthetic positive asserting the exact emitted fact shape, a minimal-pair negative that
  mints nothing, a synthetic composition proving that key can join existing inference, and
  a larger-construction probe that refuses partial reading. Conversion-specific null controls
  remain mandatory in addition to these reader controls.
- After each class lands, re-measure the banked zeros against the new join surface before
  starting the next class (the 8d/9d lesson).

Measured class order (Phase A baseline; re-survey after every landed reader):
1. **entity-in-raw-or**: conjunctive disjuncts ("either P and Q, or ¬P and R") —
   best cross-split stack estimate and Stage 3 machinery already exists.
2. **entity-raw-other**, first split into real construction families — the label is a survey
   catch-all, never one implementation increment. Choose the cheapest cross-split buyer.
3. **One narrow passive or relative-clause family** — broad measured surfaces, but heuristic
   labels require construction-level pricing before code; passive has the more balanced gain.
4. **entity-in-raw-if** and compound generics — banked until re-measurement produces a
   two-split buyer.
5. **Do-support negation VR** — 63 train / 41 holdout items but zero estimated marginal
   stack gain on both splits; demoted until another reader changes its join surface.
6. **Scope-marked universals** ("All X are not Y"): a designed stage — an
   unresolved-scope fact marker consumable only by scope-invariant verdicts (the MRS
   underspecification borrowing). Only if Phase A shows the class has verdict-gold buyers.
7. **paraphrase-gap** stays LAST — it is the composition frontier
   (`composition-design.md` stacks), the steepest cost curve.

Progress: reader 1 serves the repeated ground **both-or-neither** subtype as
an exact `A(X) ↔ B(X)` fact. It moves fully-read premises +2 / +5 and
stack-ready stories +1 / +1 on dev-train / dev-holdout with every hazard and
verdict outcome unchanged. Other `entity-in-raw-or` surfaces remain unserved
and must be priced as separate constructions; see the landed record in
`projects/scratch/ROADMAP.md`.

Reader 2 serves unrestricted generic **“CLSs are [either] L or R”** using the
existing quantified-disjunction machinery. Incremental movement is +2 / +1
fully-read premises and +0 / +1 stack-ready stories, again with no verdict or
hazard movement.

Reader 3 serves negative two-article generics **“A/An CLS is not a/an PRED”**
as an existing negative `Quantified` fact. Incremental movement is +2 / +2
fully-read premises and +0 / +0 stack-ready stories, with no verdict,
truth-scope, or hazard movement. Three construction classes are now served,
satisfying only Phase C's class-count condition; every numeric coverage
threshold still binds.

The `entity-raw-other` survey also banked two false unifications. “There is …”
is not one reader family: the train buyer is a conjoined-property existential,
while the holdout forms additionally need class/PP phrase composition. Direct
passive-agent premises likewise need either participle lemma coverage or
multi-token name handling before the measured train and holdout surfaces share
one exact key contract. Neither enabler is bought alone.

Reader 4 serves **“Everyone who V P V2 Q”** as a universal implication between
the existing flat verbal keys. A new opt-in `single_word` slot gate refuses
condensed particle/perfect verbs whose base-lemma render would erase part of
the predicate. Incremental movement is +2 / +1 fully-read premises and +0 / +0
stack-ready stories, with no verdict, truth-scope, or hazard movement. The
campaign now serves four construction classes, but remains far below every
numeric Phase C threshold.

Reader 5 serves **“If a CLS V P, then it is Q”** through the existing
class-scoped `Conditional` fact and reader 4's `single_word` key-safety gate.
Incremental movement is +2 / +3 fully-read premises, -2 / -3 truth-scope
vetoes, and +0 / +0 stack-ready stories, with no verdict or hazard movement.
Five construction classes are now served; numeric Phase C thresholds still
bind independently.

Reader 6 serves **“If NAME is not P, then NAME is Q”** through the new
dedicated `GroundConditional` fact (¬P(e) → Q(e), structural negation, a name
never rides `Conditional.cls`) and one `unless`-free fire synth — the
contrapositive comes free through the Stage 9i reductio engine and is pinned,
not built. The initially landed literal-`he` form was removed because it
assumed coreference without evidence; pronoun consequents remain banked.
Incremental movement is +2 / +0 fully-read premises, -2 / 0
truth-scope vetoes, and +0 / +0 stack-ready stories, with no verdict or
hazard movement. Six construction classes are served; every numeric Phase C
threshold still binds.

Reader 7 serves **“If people are P, then they are [not] Q”** as the
plural-agreeing twin of the existing `someone` conditional, emitting the
existing `Quantified` fact with singular-folded keys. Incremental movement is
+2 / +6 fully-read premises, -2 / -6 truth-scope vetoes, and +0 / +0
stack-ready stories; fact-bearing, verdict outcomes/reasons, and hazards do
not increase. Copular positive/negative consequences are the whole class:
verbal, do-support, negated-antecedent, and singular-`someone` siblings remain
separate constructions. Seven construction classes are served; every numeric
Phase C threshold still binds.

Reader 8 serves **“CLSs who are P are [not] Q”** through the existing
class-scoped `Conditional`: class membership and the relative property are
both required before the consequence instantiates. Incremental movement is
+2 / +3 fully-read premises, -2 / 0 truth-scope vetoes, and +0 / +0
stack-ready stories. Outcomes remain neutral; the holdout fallback-conflict
hazard improves from collision 12→9 and quarantine 24→18. Negative/verbal
relatives, verbal consequences, and definite/counted/singular subjects remain
separate. Eight construction classes are served; every numeric Phase C
threshold still binds.

Reader 9 serves **“Everyone RESTRICTION is [either] L or R”** through the
existing `QuantifiedDisjunction` fact. `Everyone` supplies the universal
variable while the non-empty restriction is the joinable antecedent key;
bare `or` remains inclusive and overt `either` exclusive. Incremental
movement is +2 / +3 fully-read premises, −2 / −3 truth-scope vetoes, and
+1 / +0 stack-ready stories on dev-train / dev-holdout. Outcomes and hazards
remain neutral. Nine construction classes are served; every numeric Phase C
threshold still binds.

Reader 10 serves **“A/An CLS is either a/an L or a/an R”** through the same
`QuantifiedDisjunction` machinery. Requiring both predicate articles proves
the disjuncts are nominal even when their words are unknown; a broader
articleless draft was rejected after a synthetic quarantined-verb refusal
failed. Incremental movement is +2 / +3 fully-read and fact-bearing premises,
−2 / −3 truth-scope vetoes, and +0 / +0 stack-ready stories on dev-train /
dev-holdout. Outcomes and hazards remain neutral. Ten construction classes
are served; every numeric Phase C threshold still binds.

Reader 11 serves **“No CLSs have P” / “No CLS has P”** through negative
`Quantified` facts. Agreement normalizes both predicates to `have P`, while
only the plural class key folds; verb/modal class-span blocks and strict
predicate blocks refuse relative, modal, perfect, double-negative, and
coordinated forms. Incremental movement is +1 / +3 fully-read premises,
+1 / +1 fact-bearing premises, −1 / −3 truth-scope vetoes, and +0 / +0
stack-ready stories on dev-train / dev-holdout. Outcomes and hazards remain
neutral. Eleven construction classes are served; every numeric Phase C
threshold still binds.

Reader 12 serves plural-agreeing **“No CLSs V P”** event universals through
the same negative `Quantified` representation. A bare-form, single-token
non-state verb is the agreement and key-preservation gate; structural blocks
for `who`/`that`/`which` relative-marker senses prevent a relative verb from
being mistaken for the main verb. Incremental movement is +4 / +3 fully-read
premises, +0 / +0 fact-bearing premises, −4 / −3 truth-scope vetoes, and +0 /
+0 stack-ready stories on dev-train / dev-holdout. Outcomes and hazards remain
neutral. Twelve construction classes are served; every numeric Phase C
threshold still binds.

Reader 13 serves named ground **“NAME does not V P”** event denials as exact
negative `Atom` facts. The existing `nonstate_verb`, `bare_form`, and
`single_word` gates preserve the ground-verbal key while refusing copular,
stative-possession, particle, perfect, coordinated, counted, and multi-verb
surfaces. Incremental movement is +4 / +0 fully-read premises, +0 / +0
fact-bearing premises, −4 / 0 truth-scope vetoes, and +0 / +0 stack-ready
stories on dev-train / dev-holdout. Outcomes and hazards remain neutral.
Thirteen construction classes are served; every numeric Phase C threshold
still binds. The adjacent outer-quantified subject-relative verbal prototype
was re-measured and removed after adding a valid fact but moving no registered
metric; stative ownership remains a separate unbought class.

Reader 14 serves bare-plural **“CLSs will either V P or V2 Q”** future-event
disjunctions as exclusive `QuantifiedDisjunction` facts. Literal `will`
provides the exact tense skeleton (the broader `future_modal` slot also admits
ordinary auxiliaries and was removed after falsification). Both branches require
bare-form, single-token `nonstate_verb` heads and predicate spans that refuse
sign, coordination, further verbs/modals, and counted material. Incremental
movement is +4 / +0 fully-read premises, +0 / +0 fact-bearing premises, −4 / 0
truth-scope vetoes, and +0 / +0 stack-ready stories on dev-train / dev-holdout.
Outcomes and hazards remain neutral. Fourteen construction classes are
served; every numeric Phase C threshold still binds.

Reader 15 serves singular indefinite **“A/An CLS will not V P”** future-event
generics as negative `Quantified` facts. Literal `will` avoids the ask-oriented
`future_modal` auxiliary breadth; the event head is bare-form, single-word,
and non-state, while both class and predicate spans refuse larger signed,
coordinated, modal, verbal, and counted constructions. Incremental movement
is +4 / +0 fully-read premises, +0 / +0 fact-bearing premises, −4 / 0
truth-scope vetoes, and +0 / +0 stack-ready stories on dev-train / dev-holdout.
Outcomes and hazards remain neutral. Fifteen classes are served; every Phase
C threshold still binds.

Reader 16 serves named **“NAME has P or V Q”** mixed possession/event
disjunctions as inclusive ground `Disjunction` facts. The possession branch
canonicalizes to `have P`; the event branch lemma-renders to the existing
ground-verbal key. Separate span gates refuse scoped/quantified possession,
either-marking, sign, coordination, modals, further verbs, particles, and
counted material. Incremental movement is +4 / +0 fully-read premises, +0 / +0
fact-bearing premises, −4 / 0 truth-scope vetoes, and +0 / +0 stack-ready
stories on dev-train / dev-holdout. Outcomes and hazards remain neutral.
Sixteen classes are served; every Phase C threshold still binds.

Reader 17 serves singular **“Every CLS has P”** positive possessive universals
as `Quantified(cls, "have P", true)`. A dedicated state-syntax rule preserves
the `nonstate_verb` boundary; class and predicate spans refuse quantifier
scope, either-marking, coordination, relatives, modals, verbs, and counted
material. Incremental movement is +2 / +0 fully-read premises, +0 / +0
fact-bearing premises, −2 / 0 truth-scope vetoes, and +0 / +0 stack-ready
stories on dev-train / dev-holdout. Outcomes and hazards remain neutral.
Seventeen classes are served; every Phase C threshold still binds.

Reader 18 serves plural-generic **“If people are P, then they V Q”**
copular-to-verbal conditionals as positive `Quantified` facts. The antecedent
uses reader 7's singular-folded key contract; the bare, single-token non-state
consequence renders exactly like named ground-verbal facts and questions.
Incremental movement is +2 / +0 fully-read and fact-bearing premises, −2 / 0
truth-scope vetoes, and +0 / +0 stack-ready stories on dev-train /
dev-holdout. Train agreement ambiguity improves by two; outcomes and all
other hazards remain neutral. The broader unrestricted verbal-to-verbal
prototype was removed after matching zero DEV premises. Eighteen classes are
served; every Phase C threshold still binds.

Reader 19 serves indefinite-generic **“If a/an CLS V P, [then] they V2 Q”**
conditionals through paired explicit-`then` and comma-only readers. The
article licenses the singular generic, the antecedent event uses a
third-person-singular head, and the pronoun consequence uses a bare-form
event head; both keys echo ground-verbal. Incremental movement is +2 / +0
fully-read premises, −2 / 0 truth-scope vetoes, and +0 / +0 stack-ready
stories on dev-train / dev-holdout. The holdout-looking `gains knowledge`
surface remains blocked by unknown vocabulary. Nineteen classes are served;
every Phase C threshold still binds.

Reader 20 serves reduced-relative people universals **“People V P are Q”**
as positive `Quantified` facts keyed by the exact reduced-relative verb
phrase. A shared morphology correction makes a one-content-unit `.singular`
span follow the same capitalized fallback-name fold as a one-unit slot; this
is what lets plural `Americans` join singular `American`, while multi-unit
names remain exact. Incremental movement is +0 / +1 fully-read premises,
0 / −1 truth-scope vetoes, and +0 / +1 stack-ready stories on dev-train /
dev-holdout. One holdout item safely converts declined → correct; no hazard
increases. Twenty classes are served; every Phase C threshold still binds.

Reader 21 serves fully repeated ground equivalences **“NAME is either both A
and B or neither A nor B.”** A reusable `same_phrase` rule predicate requires
the two negative-branch spans to render exactly like the positive branch
before emitting the existing `Equivalence` fact. Incremental movement is
+0 / +2 fully-read premises, 0 / −2 truth-scope vetoes, and +0 / +1
stack-ready stories on dev-train / dev-holdout. Two holdout items safely
convert declined → correct through existing equivalence propagation,
disjointness, reductio, and modus tollens. Twenty-one classes are served;
every Phase C threshold still binds.

Reader 22 serves implicit-restrictor property universals **“Anything P is Q”**
and **“No one P is Q.”** The two surfaces emit positive and negative
`Quantified(P, Q)` facts. The narrow negative sibling supplies the exact
`P → not Q` key alongside the older generic fallback's over-literal key,
allowing the existing universal-chain synth to derive `lazy → not energetic`.
Incremental movement is +0 / +2 fully-read premises, 0 / 0 truth-scope
vetoes, and +0 / +1 stack-ready stories on dev-train / dev-holdout. Outcomes
and hazards remain neutral. Twenty-two classes are served; the holdout
stack-story threshold is met exactly at 10, while the fully-read, veto, and
train stack thresholds remain conjunctively unmet.

Reader 23 serves second-person generic conditionals **“If you are a P, then
you are a Q.”** Repeated generic `you` denotes one universally bound variable,
so the construction emits positive `Quantified(P, Q)` without discourse
coreference. Incremental movement is +0 / +5 fully-read premises, 0 / −5
truth-scope vetoes, and +0 / +0 stack-ready stories on dev-train /
dev-holdout. The target tennis story becomes premise-complete and derives the
exact champion-to-professional-player chain; its asks remain unread. Outcomes
and hazards are neutral. Twenty-three classes are served; the holdout
stack-story threshold remains met while the other conjunctive thresholds bind.

Reader 24 serves missing terminal boundaries between a premise and question.
A capitalized token only proposes the split; one read rule must wholly consume
the left fragment and emit a fact, while one ask rule must wholly consume the
right. Incremental movement is +0 / +5 fully-read premises and +0 / +1
stack-ready stories on dev-train / dev-holdout; the holdout premise denominator
also rises by five as the previously omitted final premise is restored. Truth
vetoes, outcomes, and hazards remain neutral. Twenty-four classes are served;
holdout stack readiness reaches 11 stories, while the other conjunctive
thresholds remain unmet.

Reader 25 serves active reduced-relative possessive universals **“Everyone
V-ing P has Q.”** An opt-in `present_participle` morphology gate requires an
`-ing` surface whose registered lemma differs, distinguishing the non-finite
restrictor from a finite or accidentally `-ing`-final bare verb. The reader
emits exact `Quantified(V(P), have(Q))` keys. Incremental movement is +6 / +0
fully-read premises and +1 / +0 stack-ready stories on dev-train /
dev-holdout; fact-bearing, truth-scope vetoes, outcomes, and hazards remain
neutral. The buyer is now ready for deeper disjunctive case reasoning, which
remains a separate inference increment. Twenty-five classes are served; the
fully-read, veto, and train-stack thresholds remain unmet.

Reader 26 serves plural-agreeing positive possessive universals **“All CLSs
have P.”** The `All`/bare-`have` agreement licenses singularizing the class;
the predicate stays echo-exact. Relative, signed, modal, coordinated,
quantified-object, multi-verb, and merged-counted siblings refuse. Incremental
movement is +7 / +4 fully-read premises, −7 / −4 truth-scope vetoes, and +1 /
+0 stack-ready stories on dev-train / dev-holdout. One train item safely
converts declined → correct through the existing negative-chain synthesizer;
hazards remain neutral. Twenty-six classes are served; the fully-read, veto,
and train-stack thresholds remain unmet.

Reader 27 serves comma-bound free-relative verbal conditionals **“If a/an CLS
V P, they V2 what SUBJECT V3 Q.”** The embedded subject and verb remain inside
one exact outer consequence key; they do not mint another proposition. An
auxiliary guard prevents `do` from being absorbed into the embedded subject,
and explicit-`then`, signed, modal, coordinated, perfect/particle, and counted
siblings refuse. Incremental movement is +1 / +0 fully-read premises, −1 / 0
truth-scope vetoes, and +1 / +0 stack-ready stories on dev-train /
dev-holdout. The buyer remains undetermined because its ground class fact and
conditional event antecedent do not yet join; that bridge is a separate
construction/inference decision. Hazards and outcomes remain neutral.
Twenty-seven classes are served; the fully-read, veto, and train-stack
thresholds remain unmet.

Reader 28 serves inclusive two-article indefinite-generic disjunctions
**“A/An CLS is a/an L or a/an R.”** The articles structurally prove the
generic class and nominal branches without vocabulary admission. Bare `or`
emits `QuantifiedDisjunction(exclusive=false)`, so shared case analysis applies
but XOR branch elimination does not. Signed, coordinated, verbal,
prepositional, articleless, either-marked, and larger siblings refuse.
Incremental movement is +2 / +0 fact-bearing and fully-read premises, −2 / 0
truth-scope vetoes, and +1 / +0 stack-ready stories on dev-train /
dev-holdout. The buyer’s remaining named-object property substitution is a
separate inference class. Hazards and outcomes remain neutral. Twenty-eight
classes are served; the fully-read, veto, and train-stack thresholds remain
unmet.

Reader 29 serves active-participial compound verbal universals **“V-ing CLSs
V2 P.”** The participle and singularized plural head form an exact class key;
the bare-form main verb preserves ground-verbal predicate rendering. Definite
subjects, finite/adjectival modifiers, singular classes, signed, modal,
coordinated, state, particle/perfect, relative, and counted siblings refuse.
Incremental movement is +0 / +1 fully-read premises, 0 / −1 truth-scope
vetoes, and +0 / +1 stack-ready stories on dev-train / dev-holdout. The buyer
remains undetermined because its longer coordinated ground class has no exact
subclass bridge. Agreement ambiguity improves by one; no hazard increases.
Twenty-nine classes are served; the fully-read, veto, and train-stack
thresholds remain unmet.

Reader 30 serves named-PP existential premises **“There is a/an CLS
PREPOSITION NAME.”** Typed noun/name boundaries plus a claimed terminal period
prevent prefix truncation of relative or passive tails. The reader emits an
`Existential` fact and never invents a witness. Plural copulas, other
determiners, signed/coordinated classes, common/count objects, and larger
clauses refuse. Incremental movement is +0 / +3 fact-bearing and fully-read
premises, +0 / +1 stack-ready stories, and no truth-scope-veto movement on
dev-train / dev-holdout. Existing consumers do not chain existentials through
universals, so the buyer remains undetermined. Hazards and outcomes are
neutral. Thirty classes are served; the fully-read, veto, and train-stack
thresholds remain unmet.

Reader 31 serves direct passive named-agent premises **“The PATIENT is V-ed
by NAME.”** A new opt-in `past_participle` morphology gate requires `-ed`/`-en`
surface morphology plus a registered lemma change; the reader reverses the
surface roles into the existing `VerbalRelation(NAME, V, PATIENT)`. Definite
and terminal boundaries plus a guarded patient span keep other copulas,
finite/bare/self-lemmed verbs, sign, coordination, indefinite/common agents,
and larger tails unread. Incremental movement is +2 / +0 fully-read premises
and +1 / +0 stack-ready stories on dev-train / dev-holdout; fact-bearing,
truth-scope vetoes, outcomes, and hazards remain neutral. Thirty-one classes
are served; the fully-read, veto, and train-stack thresholds remain unmet.

Reader 32 serves PP-restricted negative verbal universals **“None of the CLSs
PREPOSITION R V the P.”** A typed bare-plural head and bare-form event verb
prove generic agreement; one explicit PP remains in the exact restrictor key,
and both definite articles plus the terminal period are claimed. The reader
emits negative `Quantified` facts. Relative, multi-PP, signed, modal,
coordinated, counted, perfect, and larger-tail siblings remain unread.
Incremental movement is +2 / +0 fully-read premises and +1 / +0 stack-ready
stories on dev-train / dev-holdout; fact-bearing, truth-scope vetoes,
outcomes, and hazards remain neutral. Thirty-two classes are served; the
fully-read, veto, and train-stack thresholds remain unmet.

Reader 33 serves reversed named memberships **“One of the CLSs of OWNER was
MEMBER.”** The first `of` provides the partitive skeleton while the second
stays inside the exact owned-class key. Because the witness is identified,
the reader emits positive `Atom(MEMBER, singular(CLS)+of+OWNER)` rather than
an existential. Counts, missing articles/owners, extra PPs, other copulas,
sign, nominal/pronominal members, coordination, adjuncts, apposition,
modality, relatives, and larger siblings remain unread. Incremental movement
is +0 / +2 fully-read premises and +0 / +1 stack-ready stories on dev-train /
dev-holdout; fact-bearing, truth-scope vetoes, outcomes, and hazards remain
neutral. Thirty-three classes are served; the fully-read, veto, and
train-stack thresholds remain unmet.

Reader 34 serves exactly-three named distributive copular subjects **“A, B
and C are P”** and the Oxford-comma sibling. It extends the existing two-name
rule, singular-folding the shared plural-agreeing predicate and emitting one
positive `Atom` per name. The inherited article refusal excludes collective
predicates; signed, disjunctive, non-name, shorter, and longer siblings remain
unread. Incremental movement is +2 / +2 fact-bearing and fully-read premises
and −2 / −2 truth-scope vetoes on dev-train / dev-holdout; stack readiness,
outcomes, and hazards remain neutral. Thirty-four classes are served; the
fully-read, veto, and train-stack thresholds remain unmet. The rechecked
`If someone is P, then they V Q` sibling stays banked because its sole
apparent DEV buyer has an ambiguous event head and the safe prototype matches
zero rows.

Reader 35 serves reversed definite role memberships **“The ROLE of OWNER
is/was MEMBER.”** Paired tense readers emit positive
`Atom(MEMBER, ROLE+of+OWNER)` without asserting identity, aliasing, or a bare
role. Definite and terminal boundaries plus a final proper-name gate keep
indefinite, signed, coordinated, modal, relative, appositive, and larger
siblings unread. Incremental movement is +1 / +2 fully-read premises on
dev-train / dev-holdout; fact-bearing, truth-scope vetoes, stack readiness,
outcomes, and hazards remain neutral. Thirty-five classes are served; the
fully-read, veto, and train-stack thresholds remain unmet. A structural
prefixed-verb reader remains banked: tokenization erases the hyphen in the
apparent `co-produced` train closer, and its exact predicate has no existing
conclusion or inference join.

Reader 36 serves exactly-four asyndetic named copular lists **“A, B, C, D are
P.”** Three required comma boundaries distinguish it from reader 34's
three-name conjunction/Oxford-comma class. It singular-folds the shared
plural-agreeing predicate and emits one positive `Atom` per name; the same
article refusal excludes collective predicates. Shorter/longer lists,
conjunction, disjunction, missing punctuation, non-name members, sign, and
apposition remain unread. Incremental movement is +0 / +2 fact-bearing and
fully-read premises and +0 / +1 stack-ready stories on dev-train /
dev-holdout; vetoes, outcomes, and hazards remain neutral. Thirty-six classes
are served; the fully-read, veto, and train-stack thresholds remain unmet.
The newly exposed coordinated counted-existential train closer stays banked
because condensation splits its hyphenated counted classes and no existing
key renderer can remove the cardinal without partial reading.

Reader 37 serves past indefinite existentials with definite PP descriptions:
**“There was a/an CLS PREPOSITION the DESCRIPTION.”** The construction emits
an `Existential` with the complete indefinite class and exact qualified PP
predicate, without inventing a witness. Incremental movement is +2 / +0
fact-bearing and fully-read premises and +1 / +0 stack-ready stories on
dev-train / dev-holdout; vetoes, outcomes, and hazards remain neutral.
Thirty-seven classes are served. A preceding attempt to admit `left` as the
irregular past of `leave` bought the Bayern train story but failed the shared
suite by rerouting arithmetic remainder asks, so it was reverted and banked.

Reader 38 serves definite-description ground copular memberships **“The
DESCRIPTION is a/an PREDICATE.”** It emits one exact positive `Atom` for the
described referent rather than turning the definite NP into a generic class.
Incremental movement is +0 / +2 fact-bearing premises, +2 / +4 fully-read
premises, and +1 / +0 stack-ready stories on dev-train / dev-holdout;
vetoes, outcomes, and hazards remain neutral. Thirty-eight classes are
served, and the train stack-ready threshold is now 21/22 stories.

Reader 39 serves definite-description memberships with reduced passive
relatives **“The DESCRIPTION is a/an CLS V-ed REST.”** It emits the entailed
base-class atom plus the exact restricted-property atom, using the predicate
article, noun category, productive past-participle morphology, and complete
sentence boundary as its proof. Incremental movement is +0 / +0 fact-bearing,
+1 / +0 fully-read premise, and +1 / +0 stack-ready item/story on dev-train /
dev-holdout; vetoes, outcomes, and hazards remain neutral. Thirty-nine classes
are served. Both stack-story thresholds are now met, but the fully-read and
truth-scope-veto thresholds remain conjunctively unmet, so Phase C and TEST
look #6 are not scheduled.

Reader 40 serves restricted plural-generic verbal conditionals **“If people
RESTRICTION V P, then they V2 Q.”** It maps the restriction and antecedent
event to the existing `Conditional` antecedent pair and requires bare,
single-token event heads. Incremental movement is +0 / +1 fact-bearing and
fully-read premise, 0 / −1 truth-scope veto, and +0 / +0 stack-ready stories
on dev-train / dev-holdout; outcomes and hazards remain neutral. Forty classes
are served. A broader articleless-disjunction candidate was banked when its
buyer-preserving grammar admitted ambiguous finite verbs. Phase C and TEST
look #6 remain unscheduled.

Reader 39 was subsequently corrected after review: its noun-category class
slot had rendered ambiguous noun **“building”** through verb lemma `build`.
Both emitted predicates now preserve the noun surface, and a narrow mirrored
reduced-passive question shape uses the identical key. The correction is
neutral on all ten DEV gates and changes no campaign metric.

Reader 41 serves reduced-passive unrestricted-object disjunctions
**“Everything V-ed RESTRICTION is either a/an L or a/an R.”** It uses the
existing productive-participle gate, exact restricted class key, and
noun-category disjuncts; the logic pack supplies only the missing overt
`displayed → display` morphology. Incremental movement is +1 / +0
fact-bearing and fully-read premise, −1 / 0 truth-scope veto, and +0 / +0
stack-ready stories on dev-train / dev-holdout. Outcomes and hazards remain
neutral. Forty-one classes are served; Phase C and TEST look #6 remain
unscheduled.

Reader 42 serves implicit-restrictor negative possession universals
**“Nothing RESTRICTION has P.”** It emits the existing negative `Quantified`
fact with an exact restriction and canonical `have P` consequence.
Incremental movement is +2 / +0 fact-bearing and fully-read premises, −2 / 0
truth-scope vetoes, and +0 / +0 stack-ready stories on dev-train /
dev-holdout. Outcomes and hazards remain neutral. Forty-two classes are
served; Phase C and TEST look #6 remain unscheduled.

Reader 43 serves implicit-restrictor property universals
**“Everything RESTRICTION is PROPERTY.”** It emits the existing positive
`Quantified` fact with exact restriction and consequence keys. Incremental
movement is +2 / +0 fact-bearing and fully-read premises, −2 / 0 truth-scope
vetoes, and +0 / +0 stack-ready stories on dev-train / dev-holdout. Outcomes
and hazards remain neutral. Forty-three classes are served; Phase C and TEST
look #6 remain unscheduled.

Reader 44 serves appositive-restricted plural possession disjunctions
**“CLSs RESTRICTION, APPOSITIVE have either a/an MODIFIER NOUN or a/an
MODIFIER NOUN.”** It emits the existing exclusive `QuantifiedDisjunction`
with the complete class and `have` branch keys; noun compounds render through
their surfaces so modifiers survive. Incremental movement is +6 / +0 fact-
bearing and fully-read premises, −6 / 0 truth-scope vetoes, and +0 / +0
stack-ready stories on dev-train / dev-holdout. Outcomes and hazards remain
neutral. Forty-four classes are served; Phase C and TEST look #6 remain
unscheduled.

Reader 45 serves reduced-passive possessive existentials
**“Some CLSs V-IRREG by AGENT have a/an PROPERTY.”** It emits the existing
`Existential` fact with the full restricted witness class and exact `have`
property; the matching ask reaches the existing existential consumer without
minting a witness. Incremental movement is +0 / +3 fact-bearing and fully-read
premises, 0 / −3 truth-scope vetoes, and +0 / +0 stack-ready stories on
dev-train / dev-holdout. Outcomes and hazards remain neutral. Forty-five
classes are served; Phase C and TEST look #6 remain unscheduled.

Reader 46 serves bare-name indefinite possession **“NAME has a/an MODIFIER
NOUN.”** It emits an exact positive ground `Atom(NAME, have MODIFIER NOUN)`;
the mirrored ask composes through the existing verdict consumer. The
noun-category compound preserves modifiers while refusing larger phrases and
unsafe skipped-comma boundaries. Incremental movement is +0 / +1 fully-read
premise, 0 / −1 truth-scope veto, and +0 / +0 stack-ready stories on dev-train
/ dev-holdout; fact-bearing, outcomes, and hazards remain neutral. The reader
also buys the ground-Atom prerequisite for a named-possession conditional.
Forty-six classes are served; Phase C and TEST look #6 remain unscheduled.

Reader 47 serves positive same-name possession conditionals **“If NAME has
[a/an] PROPERTY, then NAME is a/an PROPERTY.”** A dedicated
`PositiveGroundConditional` preserves Reader 6's negative-only fact contract
and fires only from an exact positive Atom; Reader 46 composition is pinned.
Incremental movement is +0 / +1 fact-bearing and fully-read premise, 0 / −1
truth-scope veto, and +0 / +0 stack-ready stories on dev-train / dev-holdout.
Outcomes and hazards remain neutral. Forty-seven classes are served; Phase C
and TEST look #6 remain unscheduled.

Post-Reader-47 lexical activation adds pack-scoped `act/acts` and `prevent`,
making the pre-existing Stage 9f **“Some CLSs VERB OBJECT”** reader and ask
reachable for one train premise. Incremental movement is +1 / +0 fact-bearing
and fully-read premise, −1 / 0 truth-scope veto, and +0 / +0 stack-ready
stories. It changes no grammar, inference, outcome, or hazard and earns no new
construction-class credit; forty-seven classes remain served.

Reader 48 serves plural-agreeing intransitive existentials **“Some CLSs
VERB.”** It emits the existing positive `Existential(CLS, VERB)` fact and
reuses the existing consumer without inventing an object. Incremental movement
is +1 / +0 fact-bearing and fully-read premise, −1 / 0 truth-scope veto, and
+0 / +0 stack-ready stories on dev-train / dev-holdout. Outcomes and hazards
remain neutral. The cross-split `All CLSs are not PROPERTY` candidate stays
banked because the earlier v1 falsification records mixed scope judgments and
a confident wrong. Forty-eight classes are served.

Reader 49 serves restricted past-passive existentials **“Some CLSs
RESTRICTION were V-ed REST.”** It emits the existing positive `Existential`
with the complete restricted class and tense-normalized passive property;
productive participle morphology proves voice. Incremental movement is +1 /
+0 fact-bearing and fully-read premise, −1 / 0 truth-scope veto, and +0 / +0
stack-ready stories on dev-train / dev-holdout. Outcomes and hazards remain
neutral. Forty-nine classes are served.

Reader 50 serves modal-passive existentials **“Some CLSs can be V-ed REST.”**
It retains the modal inside the exact property key, so possibility is not
asserted as actuality; productive participle morphology proves passive voice.
Incremental movement is +1 / +0 fact-bearing and fully-read premise, −1 / 0
truth-scope veto, and +0 / +0 stack-ready stories on dev-train / dev-holdout.
Outcomes and hazards remain neutral. Qualified nouns remain banked because
their condensed qualifier is deliberately refused by `bare_plural`, and the
modal supplies no independent agreement signal. Fifty classes are served.

Post-Reader-50 lexical activation adds pack-scoped `supported → support` and
`researched → research`, making the pre-existing Stage 6 ground-verbal reader
reachable for two train premises. Incremental movement is +2 / +0
fact-bearing and fully-read premises, −2 / 0 truth-scope vetoes, and +0 / +0
stack-ready stories. Grammar, inference, outcomes, and hazards remain neutral;
fifty classes remain served.

Reader 51 serves fronted predicative adjuncts plus ground events **“After
being ADJECTIVE, NAME V-ed REST.”** It emits only the complete normalized
main-event `Atom`, not an independent adjunct property. Incremental movement
is +1 / +0 fact-bearing and fully-read premise, −1 / 0 truth-scope veto, and
+0 / +0 stack-ready stories on dev-train / dev-holdout. Outcomes and hazards
remain neutral. The bare-plural present-event disjunction candidate is banked
until its subject/verb/possessive-object token boundary is independently
proved. Fifty-one classes are served.

Reader 52 serves appositive role identities with explicit relative events
**“The ROLE of OWNER, MEMBER, is a CLS who V REST.”** It emits exact role,
class, and event `Atom`s because punctuation and `who` bind all three to the
named member without heuristic coreference. Incremental movement is +1 / +0
fact-bearing and fully-read premise, −1 / 0 truth-scope veto, and +0 / +0
stack-ready stories on dev-train / dev-holdout. The buyer completes premise
reading for one story, but its existential-relative ask remains unrepresented.
Outcomes and hazards remain neutral. Fifty-two classes are served.

Post-Reader-52 inference adds exact existential predicate chaining:
`∃(C ∧ P)` plus `∀(P → [¬]Q)` entails `∃(C ∧ [¬]Q)`, preserving the original
witness class. It solves one train and one holdout verdict with no regression;
fully-read, veto, stack-ready, hazard, and class counts remain unchanged. The
distinct witness-class lifting operation remains a separate candidate.

The separately gated witness-class lift adds `∃(C ∧ [¬]P)` plus `∀(C → Q)`
entails `∃(Q ∧ [¬]P)`. It solves one train verdict and no holdout verdict with
no regression; fully-read, veto, stack-ready, hazard, and class counts remain
unchanged. Exact predicate mismatch continues to block the remaining
juvenile-delinquent query and is not normalized away.

Post-inference lexical activation adds pack-scoped `plots → plot` and bare
`swallow`, making the existing Stage 6 ground reader consume one train
controlled-event premise. Incremental movement is +1 / +0 fact-bearing and
fully-read premise, −1 / 0 veto, and +0 / +0 stack-ready stories. Outcomes,
hazards, and class credit remain unchanged. `Some CLSs that have P have Q`
stays banked pending a sound compound boundary for `well-attended weddings`.

Reader 53 serves local same-subject coordination **“NAME is a/an CLS, and it
is not P.”** Punctuation and the immediate pronoun establish exact local
coreference without enabling a general resolver. Incremental movement is +1 /
+0 fact-bearing and fully-read premise, −1 / 0 veto, and +0 / +0 stack-ready
stories. Outcomes and hazards remain neutral. Pack-scoped `TikTok: name`
activates the sole train buyer. Fifty-three classes are served.

Reader 54 serves modal-passive local positive coordination **“NAME can be
V-ed REST, and it is P.”** It preserves possibility inside the first exact
property and emits the comma-bound local positive property separately.
Incremental movement is +1 / +0 fact-bearing and fully-read premise, −1 / 0
veto, and +0 / +0 stack-ready stories. Outcomes and hazards remain neutral.
Fifty-four classes are served.

Reader 55 serves restrictive-only modal-passive unions **“The only CLSs that
can be V-ed REST are L and R.”** It preserves the reverse `only` direction and
the complete restricted class in an inclusive `QuantifiedDisjunction`.
Incremental movement is +1 / +0 fact-bearing and fully-read premise, −1 / 0
veto, and +1 / +0 stack-ready story (+3 / +0 items). Outcomes and hazards
remain neutral; exact sortal preservation deliberately blocks an otherwise
tempting query conversion. Fifty-five classes are served.

Reader 56 serves someone-generic verbal consequences **“If someone is P,
then they V Q.”** It treats singular `they` as bound by the generic
conditional and reuses the existing quantified-instantiation path. A
scratch-pack category selects the measured ambiguous bare event without
shadowing shared lexicon data. Incremental movement is +1 / +0 fact-bearing
and fully-read premise, −1 / 0 veto, and +1 / +0 stack-ready story (+3 / +0
items). Outcomes and hazards remain neutral. Fifty-six classes are served.

Reader 57 serves restricted someone-generic copular conditionals **“If
someone RESTRICTION is P, then they are [not] Q.”** It preserves restriction
and antecedent property as the two independent inputs to the existing
`Conditional` machinery. Incremental movement is +3 / +5 fact-bearing and
fully-read premises, −3 / −5 vetoes, and +0 / +0 stack-ready stories.
Outcomes and hazards remain neutral. Fifty-seven classes are served.

Reader 58 serves relative-class negative possession universals **“No CLSs
that NAME V have P.”** It preserves the full relative restrictor and negative
possessive consequence without object-position substitution. Incremental
movement is +0 / +10 fact-bearing and fully-read premises, 0 / −10 vetoes,
and +0 / +0 stack-ready stories. Outcomes and hazards remain neutral.
Fifty-eight classes are served.

Reader 59 serves singular-agreeing PP-restricted negative verbal universals
**“No CLS PREPOSITION RESTRICTION V P.”** It preserves the full qualified
class and uses buyer-backed 3sg morphology rather than admitting plural
siblings. Incremental movement is +0 / +9 fact-bearing and fully-read
premises, 0 / −9 vetoes, and +0 / +0 stack-ready stories. Outcomes and
hazards remain neutral. Fifty-nine classes are served.

Reader 60 serves PP-restricted indefinite copular conditionals with negative
verbal consequences **“If a/an CLS PREPOSITION RESTRICTION is P, then they do
not V Q.”** It preserves the qualified class and property as separate
antecedents. Incremental movement is +10 / +0 fact-bearing and fully-read
premises, −10 / 0 vetoes, and +0 / +0 stack-ready stories. Outcomes and
hazards remain neutral. Sixty classes are served.

Reader 61 serves exact repeated-generic copular conditionals **“If a/an CLS
is P, the CLS is Q.”** Whole-phrase equality proves witness identity without
noun-specific coreference. Incremental movement is +1 / +6 fact-bearing and
fully-read premises, −1 / −6 vetoes, and +0 / +0 stack-ready stories.
Outcomes and hazards remain neutral. Sixty-one classes are served.

Reader 62 serves restricted everyone inclusive unions **“Everyone
RESTRICTION is L, or they are R, or both.”** The final phrase proves inclusive
semantics while the full restriction remains the quantified class.
Incremental movement is +10 / +0 fact-bearing and fully-read premises,
−10 / 0 vetoes, and +0 / +0 stack-ready stories. Outcomes and hazards remain
neutral. Sixty-two classes are served.

The following pack-local lexical increment activates the pre-existing
`All CLSs V P` reader for the qualified company-device universal by admitting
`device`/`devices`, `logo`, and bare `belong`. It adds +0 / +4 fact-bearing
and fully-read premises, 0 / −4 vetoes, and no stack or outcome movement.
Inflected `belongs` and `belonging` remain unactivated, and construction-class
credit remains sixty-two. Current Phase C gaps are +9 / +21 fully read and
−64 / −72 vetoes.

The next pack-local activation admits all-caps `NBA` as an adjective. It
removes the only unread unit from a repeated copular universal on both splits,
adding +6 / +6 fully-read premises and reducing vetoes by 6 / 6 without fact,
stack, outcome, hazard, or construction-class movement. Current Phase C gaps
are +3 / +15 fully read and −58 / −66 vetoes.

Plural morphology for the already local `logo` noun then removes the only
unread unit from five train instances of a qualified Apple-product universal.
It adds +5 / +0 fully-read premises and reduces vetoes by 5 / 0 without fact,
stack, outcome, hazard, or class movement. The train fully-read threshold is
now met; remaining Phase C gaps are +15 holdout fully read and −53 / −66
vetoes.

Pack-local `defender`/`defenders` morphology next removes the only unread unit
from the soccer-role universal on both splits. It adds +3 / +6 fully-read
premises and reduces vetoes by 3 / 6 without fact, stack, outcome, hazard, or
class movement. Remaining Phase C gaps are +9 holdout fully read and −50 / −60
vetoes.

Infrastructure borrowings (each its own increment, only if Phase B friction proves the need):
- **Key-schema lint** (the SEM-I borrowing): every emitting rule declares its mintable key
  shapes; lint joins them against consumer key shapes. Catches the curly-apostrophe /
  double-render / self-lemma class at build time. Extends `rulekit lint`.
- **Verb-lemma table completion** (the 71 self-lemma verbs, 9c): a difg-mined/core-english
  pack change with repo-wide key churn — own increment, full nine-slice gate, only when a
  class (e.g. 'lives in' locatives) is measurably blocked on it.
- **Merged-verb refusal is built:** reader 4 added the opt-in `single_word` slot
  gate after the measured `gets up` key-loss probe. It is dormant for every
  existing rule and should be reused when a logical key cannot preserve a
  condensed verb's full predicate.
- **Present-participle refusal is built:** reader 25 added the opt-in
  `present_participle` slot gate. It requires inflected `-ing` morphology plus
  a distinct registered lemma, stays dormant for every pre-existing rule,
  and prevents active reduced relatives from accepting finite/bare verbs.
- **Past-participle refusal is built:** reader 31 added the opt-in
  `past_participle` slot gate. It requires productive `-ed`/`-en` morphology
  plus a distinct registered lemma, stays dormant for every pre-existing
  rule, and prevents direct passives from accepting finite/bare verbs.
- **Event-reader/state split is built:** reader 14 falsification proved bare
  `be`/`been`/`being` were escaping `nonstate_verb`, but adding them to `state`
  changed arithmetic holding semantics and produced a GSM8K confident wrong.
  Core now declares `non_event_verb` as the parent of `state`; difg-mined adds
  the three copular forms only to that broader exclusion category. This
  prerequisite is neutral on all ten snapshot gates and earns no reader or
  coverage credit.

### Phase C — the look-#6 coverage checkpoint

Look #6 is NOT scheduled off conversion count (twice-measured lesson). Phase A pre-registers
the numeric trigger; it must include ALL of:
- fragment-veto / fully-read improvement reaches its target on BOTH dev-train and the grouped
  dev-holdout, not only on the mined split;
- stack-ready coverage rises by its target across multiple distinct stories on BOTH splits;
- ≥3 blocker classes are fully served;
- contradiction, quarantine, ambiguous-reading, and wrong-hazard metrics do not increase.

The user calls the look (TEST looks are always user-directed); one aggregate-only look,
walked in commit order. The parked aggregate is 1 correct / 1 wrong / 283 declined. TEST
acceptance requires **wrong ≤1, correct ≥1, errors = 0, and precision ≥0.5**. Any wrong-count
increase reverts the responsible commit even when correct count rises enough for precision to
hold or improve; a ratio may never launder a new confident wrong.

### Phase D — the gate back to FOLIO (integration proper)

Only after a look #6 that shows nonzero transfer at held precision:
1. Re-run the Stage 5 preconditions: ladder re-measure with the real machinery, every
   commit null-controlled; the indefinite-article gate already covers the one known hazard.
2. **Recommended end state: promote `packs/logic` to top-level `packs/` and add a parallel
   `projects/folio-logic`** that loads it — making folio-logic an ATTEMPTED corpus with the
   standard bar (0 BROKE, 0 DECL→WRONG, hand-inspected commits), while `projects/folio`
   keeps loading
   `[core-english, arithmetic, difg-mined]` and remains the repo's only 0-commit safety
   gate. Flipping folio itself would forfeit that gate (the SciBench precedent shows a
   replacement corpus is expensive); revisit only if folio-logic proves stable across
   multiple TEST looks.
3. `folio-logic` references the existing `projects/folio/data/*.parquet` files. Do NOT copy
   `build_corpus.py`, re-materialize the corpus, or define a second SALT: the existing FOLIO
   builder remains the one firewall definition.
4. TEST history must not reset when the project root changes. Before the first folio-logic
   look, preserve/import the five historical ledger rows with provenance and designate one
   continuing campaign ledger; document the transition in ROADMAP/HANDOFF. A fresh project-
   scoped `snapshots/test-ledger.jsonl` must never be presented as zero prior looks.
5. Update CLAUDE.md (gate table) and `docs/HANDOFF.md`; per standing instruction, push
   after each landed batch.

## Files touched (implementation phase, for scoping only)

- `projects/scratch/packs/logic/rules/logic.yaml`, `synth.yaml`, `categories/logic.yaml` —
  the Phase B readers (bulk of the work; pattern per class, one commit each).
- `projects/scratch/ROADMAP.md` — taxonomy refresh + per-stage records.
- `src/rulekit/kernel/` — only for designed stages (scope marker) or the key-schema lint;
  every kernel touch gets the full nine-slice NEUTRAL gate (shared-reader blast radius).
- Phase D: `packs/logic/` (moved), `projects/folio-logic/project.yaml`, the continuing
  TEST-ledger record/provenance, `CLAUDE.md`, `docs/HANDOFF.md`. The project references the
  existing FOLIO parquets; it owns no duplicate corpus builder.
- Scratchpad only, never committed: the Phase A classifier and any ERG survey tooling. Its
  reproducible DEV-only baseline report and metric definitions ARE committed.

## Verification

- Per increment: `uv run pytest`; `uv run rulekit --project projects/curated bench --slice
  suite`; snapshot+diff on **difg dev**, gsm8k dev-train/dev-holdout, asdiv, svamp, mawps,
  scibench, and folio (all NEUTRAL); folio-with-logic dev-train + dev-holdout diff (0 BROKE,
  0 DECL→WRONG). Pack-only scratch changes are expected to be neutral on projects that do
  not load the pack; those runs preserve the gate but do not substitute for folio-with-logic
  behavior. Kernel/core changes require the full matrix because their blast radius is live.
- Per reader increment: the four synthetic falsification/composition probes above, plus null
  controls on every conversion (swap subject/predicate/premise — the answer must move).
- Per phase: fact-bearing, fully-read/veto, stack-ready, and hazard metrics vs the Phase A
  baseline, split by grouped dev-train/dev-holdout and recorded in ROADMAP.md.
- TEST: user-directed looks only, ledgered in `projects/folio/snapshots/test-ledger.jsonl`;
  TEST-look scripts must be FILES, never heredocs (jobs>1 spawn crash, pinned in memory).
  After Phase D, follow the explicitly migrated continuing campaign ledger. Accept only when
  wrong ≤1, correct ≥1, errors = 0, and precision ≥0.5.

## Explicitly out of scope

- Any TEST mining or item-level TEST inspection (aggregate-only, forever).
- Chasing item 228, the Dickinson items, [99], or the Bayern sortal-free instantiation.
- pydelphin/ACE/ERG anywhere in the runtime or verdict path.
- difg's logic domain (8-of-8 'Yes' golds — an always-yes engine aces it).
