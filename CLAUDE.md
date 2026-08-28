# rulekit

**Continuing a session? Read `docs/HANDOFF.md` first** — the active direction,
current baseline, next action, and hard-won invariants.

Grammar-driven reading & reasoning engine. Small deterministic kernel, declarative YAML rule
packs, no LLM at runtime. Architecture: `docs/architecture.md`. Measurement discipline:
`docs/methodology.md` (DEV/TEST firewall, precision before coverage — read before any GSM8K work).

## The constitution (non-negotiable)

1. **No specific lexicon in the Python codebase.** Every word-specific fact — senses, plurals,
   lemmas, categories, synonyms, antonyms, attributes, conversions — lives in YAML packs
   (`packs/*/`). Kernel code may reference SENSES and CATEGORY NAMES as structure (e.g. the
   `state` verb category), never enumerate words. If a fix wants a word list in Python, the fix
   is wrong — move it to a pack.
2. **No one-off parsing for specific questions.** No per-problem regexes, no branch that exists
   for one benchmark item (difg's `vocab_singles` sin — ~90 solvers that never fired on unseen
   text). Coverage comes from GENERAL machinery only: ask shapes, pattern rules with category
   gates (minimum-structure: literals are grammatical skeleton only), synthesizers, and the
   generic consumers in `answer.py`. A rule must be justified by a CLASS of problems, named at
   ship time.
3. **Every increment goes through the gate**: baseline snapshot → change → `rulekit diff`
   (0 BROKE, 0 DECL→WRONG) → dev-holdout delta (0 new wrongs) → synthetic unit test (never a
   GSM8K string in `tests/`). TEST looks are spent deliberately and rarely; a TEST precision
   drop reverts the change no matter how good DEV looked.
4. **Precision before coverage.** A confident-wrong is worse than a decline. New capability may
   only move an item declined → {correct | declined}, never → wrong.

## Batch mining (`/mine`)

`/mine [count]` runs example-led Mining v2 as a multi-agent batch
(`.claude/skills/mine/SKILL.md`): a GSM8K DEV scout selects one declining
`dev-train` item per requested candidate → parallel isolated
implementers with generated evidence → constitution review → immutable
manifests in the Designer. It then STOPS for human review and the exact machine
gate. `/mine --integrate-approved` resumes only exact approved/machine-passed
revisions and lands them sequentially onto `mining/batch-<date>`, with a full
re-gate per increment. It never merges `main` or touches TEST. Protected looks
remain manual, one per landed increment in commit order; a precision drop
reverts that commit, and only survivors are fast-forwarded by hand.
`/mine --smoke` exercises the same paused pipeline with a no-op candidate.

## Commands

```
uv run pytest -q tests/test_generation_workbench.py -k aggregate            # focused example
uv run pytest -n 4 --dist=worksteal                      # full synthetic gate (parallel)
uv run pytest                                            # equivalent serial/debug path
uv run rulekit --project projects/curated bench --slice suite              # fast 71/71 regression gate (includes reference + logic-arithmetic)
uv run rulekit --project projects/gsm8k bench --slice dev-train|dev-holdout
uv run rulekit --project projects/gsm8k bench --slice dev-train --snapshot before.json
uv run rulekit --project projects/gsm8k diff before.json after.json    # ship gate
uv run rulekit --project projects/asdiv bench --slice dev --jobs 8      # CROSS-CORPUS gate (§3b) — packs mined only on GSM8K, run on ASDiv
uv run rulekit --project projects/svamp bench --slice dev --jobs 8      # 2nd CROSS-CORPUS gate — SVAMP (adversarial variations, harder)
uv run rulekit --project projects/mawps bench --slice dev --jobs 8      # 3rd — MAWPS (classic arithmetic repository)
uv run rulekit --project projects/scibench bench --slice dev --jobs 8   # 4th — SciBench (ATTEMPTED since 2026-07; standard bar: 0 BROKE, 0 DECL→WRONG)
uv run rulekit --project projects/folio bench --slice dev --jobs 8      # 5th — FOLIO LOGIC safety, the only NON-arithmetic gate (the sole want-0-commits gate)
uv run rulekit --project projects/cogs bench --slice dev-train --jobs 8 # semantic-projection DEV worklist (COGS gold graphs)
uv run rulekit --project projects/gsm8k stats                          # the mining worklists
uv run rulekit --project projects/gsm8k lint [--category NAME]         # overlaps, blast radius
uv run rulekit --project projects/gsm8k serve                          # visual designer
```

## Layout

- `src/rulekit/kernel/` — the frozen general machinery (pipeline, facts, guards, document loop)
- `packs/core-english/` — lexicon, obligations, numbers, base categories (hand-curated)
- `packs/physics/` — reusable dimension-bound physical quantities and ask shapes
- `packs/chemistry/` — reusable formula chemistry, atomic masses, and chemistry asks
- `packs/difg-mined/` — vocabulary mined from difg; `quarantine.yaml` lists words difg
  deliberately withheld (holdout poison) — CHECK IT before admitting new vocabulary
- `packs/arithmetic/` — pattern rules, ask shapes, synthesizers (the general solver families)
- `projects/curated/` — the fast 71-item regression suite; loads the reference pack required by
  its eight lookup/aggregate cases. Always run the suite through THIS project, not gsm8k.
- `projects/gsm8k/` — the benchmark project (data + snapshots gitignored)
- `projects/asdiv/` — the CROSS-CORPUS precision gate: same packs, DIFFERENT authors' problems, run
  through the same ship gate to catch confident-wrongs GSM8K structurally can't see (methodology §3b).
  `build_corpus.py` (committed) defines the DEV/TEST firewall; data gitignored, rebuild once with
  `uv run --with datasets python projects/asdiv/build_corpus.py`
- `projects/svamp/`, `projects/mawps/`, `projects/scibench/` — the 2nd–4th cross-corpus gates. SVAMP
  (adversarial variations, harshest in-domain), MAWPS (classic arithmetic repository), and SciBench
  (out-of-domain college science — ATTEMPTED since 2026-07 via the LaTeX reader; the historical
  0-commit safety expectation is retired, the bar is the standard one: 0 BROKE, 0 DECL→WRONG, and
  every new commit hand-inspected. A replacement pure-OOD 0-commit corpus is deferred until SciBench
  coverage is non-trivial). Same shape as
  asdiv; each rebuilt once with `uv run --with datasets python projects/<name>/build_corpus.py`
- `projects/folio/` — the 5th and only NON-ARITHMETIC gate: human-written first-order logic (Yale-LILY).
  Every other gate asks for a number, so none can catch the engine ASSERTING a number at logic prose;
  a committed number against its verdict/text golds scores WRONG. Expect 0 commits — since SciBench
  became an attempted corpus (2026-07) this is the SOLE expect-0-commits gate. Its firewall buckets
  by PREMISE BLOCK, not per-item (340 stories → 1,001 items), and its 'Uncertain' gold is `text`, never
  `decline` — see `docs/negative-results.md` → "The logic-corpus search" before touching either.
- `projects/cogs/` — the semantic-projection development corpus. Its pinned
  builder materializes official COGS into DEV-train/DEV-holdout, contaminated
  calibration, and aggregate-only TEST/generalization slices. `bench` routes
  this project through normalized graph scoring (exact/partial/declined/
  incorrect), not the answer judge. Data and snapshots remain gitignored.
- `projects/pmb/` — the independent semantic-projection OOD gate. Its pinned
  builder verifies the local PMB 5.1.0 release and admits only English gold
  Tatoeba rows under the bundled CC BY 2.0 raw-text notice; PMB annotations
  are ODC-BY 1.0. Train/development are inspectable and standard TEST is
  aggregate-only and one-look. Data and snapshots remain gitignored.

Mining scripts are throwaway: keep them in the session scratchpad, never the repo — recreate
from `docs/methodology.md` §4.
