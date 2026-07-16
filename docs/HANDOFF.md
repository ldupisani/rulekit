# Session handoff — 2026-07-16

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State is committed through `b1db917` on `main` (github.com/ldupisani/rulekit).
Always check `git status` / `git log origin/main..HEAD` before assuming push parity.

> ## ➡ FOLIO IS BUILT, BENCHED AND LANDED — **919 DEV items, 0 correct / 0 WRONG** (`f7b059c`).
> ## **It caught a real confident-answer on its first run** and the fix is landed (`b1db917`).
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

The fix is **"an unread NAME is a decline"** — value-accounting's *BINDABLE is not READ* contract
applied to the one value kind this consumer binds. **A dropped name carries no digits, so no
numeric guard can ever see it**; that is why this class needs its own guard and why 5 arithmetic
corpora sat on it silently. Guarded the CONSUMER, not the ask's shape (the shape is right for the
prose it was mined on), and `undetermined` still survives where nothing is unread.

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
| `projects/asdiv/` | different authors, same task | **89.4%** (42/5), characterized worklist |
| `projects/svamp/` | **adversarial variations**, harshest in-domain | **86.7%** (13/2) — start-state fix `d46484d` |
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
- pytest **1179** · lint: 0 errors, 1 intended warning (fraction-of-remnant subsumption — documentation, not a bug)
- Cross-corpus DEV: ASDiv 89.6% (43/5) · SVAMP 86.7% (13/2) · MAWPS 100% (9/0) · SciBench 0/0 ·
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
   0 DECL→WRONG**) → same for dev-holdout → synthetic pytest (never GSM8K strings) → suite holds 52/52
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

## TEST ledger (124 looks spent)

The live ledger is `projects/gsm8k/snapshots/test-ledger.jsonl` (gitignored — this file and the archive
are the only committed record). The walk, condensed:

`0/1 → 4/1 (80%) → 5/1 (83.3%) → 6/1 (85.7%, look #11 — first genuine coverage gain) → 7/1 (87.5%,
#56) → 8/1 (88.9%, #64) → 11/1 (91.7%) → 12/1 (92.3%, current floor)`

Three reverts, all caught by the firewall, all documented in `docs/negative-results.md`:
- **look #20** — the 12-word vocab batch, 6/2. Reverted; culprit later identified as `fruit`.
- **look #32** — the fruit/fruits family alone, 6/2. Reverted; `fruit` now quarantined.
- **the rate-machinery revert** — fully re-landed look-by-look (#5–#9). The culprit was
  accounting-by-existence, not the mechanisms; all four pieces are LIVE.

The 1 persistent TEST wrong is a stable §3a unseen shape, present since look #1.

## Quick commands

```
uv run pytest -q
uv run rulekit --project projects/gsm8k bench --slice suite|dev-train|dev-holdout [--snapshot F]
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
