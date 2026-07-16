# Session handoff — 2026-07-16

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State is committed and pushed through `7145a89` on `main` (github.com/ldupisani/rulekit).
Always check `git status` / `git log origin/main..HEAD` before assuming push parity.

> ## ➡ NEXT SESSION: two live frontiers — difg domain-mining (active) and the typed-gold kernel change (the big lever)

### GSM8K is DONE and stays a regression floor
dev-train **104/0 (100%)**, dev-holdout **40/0**, curated suite **52/52**, **TEST 92.3%** (12/1 —
the session high; the subject-gapping fix solved a "gave X to Y and bought Z" TEST item). Both
engine halves (ask-shape, reading) measured out as a LONG TAIL — GSM8K coverage is closed, and the
next lever was always a DIFFERENT corpus. That is now the whole game. Proof: `docs/negative-results.md`
→ "The reading gap is a LONG TAIL"; brief `docs/reading-gap.md` is CLOSED.

### FRONTIER 1 (active): difg domain-mining — `projects/difg/`, difg-DEV 0 → 32 correct, 0 wrong
The numeric slice is 197 items over 58 domains. SEVEN domains are solved via one reusable **template**:
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

**difg reports COVERAGE, NEVER precision** (79.3% of it is difg's own `example_queries`). Never quote
its number beside the GSM8K/ASDiv precision numbers. See `docs/difg-corpus-plan.md`.

### FRONTIER 2 (the big lever): the TYPED-GOLD kernel change
55.5% of difg answers are NON-numeric (quantity+unit, verdict, set, boolean, percent) and the kernel
still cannot commit them: `Answer.committed == (kind == "number")` in `answer.py`. No commit → no
score → no mining signal for physics / logic / clock / unit_conversion. Phase 0 (harness-side
`TypedGold` + `_judge`) is landed byte-neutral (`23ccbac`); the KERNEL commit-path change is the
deferred, higher-risk work that unlocks the majority of difg. Plan + phases: `docs/difg-corpus-plan.md`.

---

## The corpora (five cross-corpus gates)

Run on ANY kernel/pack change (methodology §3b, lifecycle step 6b). Each is a `project.yaml` + a
committed salt-split `build_corpus.py`; data gitignored; flows through the existing harness with zero
new code. **Adding one is a two-file recipe.**

| Project | Role | Baseline |
|---|---|---|
| `projects/gsm8k/` | the mined corpus; now a regression floor | 104/0 dev-train, TEST 92.3% |
| `projects/asdiv/` | different authors, same task | **89.4%** (42/5), characterized worklist |
| `projects/svamp/` | **adversarial variations**, harshest in-domain | **80.0%** (12/3), fresh worklist |
| `projects/mawps/` | classic arithmetic repo | **100%** (9/0), low coverage |
| `projects/scibench/` | **out-of-domain** college science; safety check | **0/0** — a rising wrong = the engine guessing |
| `projects/difg/` | multi-domain COVERAGE corpus (not precision) | 32 correct / 0 wrong, 7 domains |

The four HF-backed ones rebuild with `uv run --with datasets python projects/<name>/build_corpus.py`;
difg reads a LOCAL difg checkout (`uv run python projects/difg/build_corpus.py`, no `--with datasets`).

The gate discipline paid off — every kernel fix last session was BOUGHT by these corpora, not by
GSM8K: distributive-container guard (`5537d10`) · value-accounting multiplicity (`b49659e`) ·
synth-GroupTotal fix + consumer both paths (`2439b82`, `ab878ad`) · container+loose composition
(`6dffe56`) · subject-gapping anaphora (`22623ee`, GSM8K TEST 91.7%→92.3%) · superordinate-via-combined
(`1466051`, "pieces of litter").

## Current numbers (verified at `7145a89`)

- GSM8K dev-train **104/0** · dev-holdout **40/0** · TEST **92.3%** (12/1) · curated suite **52/52**
- pytest **1111** (verified 2026-07-16) · lint: 0 errors, 1 intended warning (fraction-of-remnant subsumption — documentation, not a bug)
- Cross-corpus DEV: ASDiv 89.4% (43/5) · SVAMP 80.0% · MAWPS 100% · SciBench 0/0 · difg 32/0
- bench wall: dev-train 16.6s → 9.0s (trace opt-out) → 1.7s at `--jobs 12`. `--jobs` defaults to 1;
  spend it in the SERIAL integration tail, never in the implementers' gates (they already run concurrently).

## The mining loop (how work ships)

1. Baselines live in `projects/gsm8k/snapshots/` — CURRENT are `conj-train.json` / `conj-holdout.json`
   (identical to head behavior; they supersede `price-*` / `pop-*` / `conv-*` / `narrow2-*`).
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
