# rulekit

**Continuing a session? Read `docs/HANDOFF.md` first** — current numbers,
baselines, the re-landing plan, and the hard-won invariants.

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

`/mine [count]` runs the mining loop as a multi-agent batch (`.claude/skills/mine/SKILL.md`):
scout → parallel Sonnet implementers in isolated worktrees (full dev gate each) → constitution
review of every diff → sequential landing onto `mining/batch-<date>` with a full re-gate per
increment. The batch STOPS at the staging branch: TEST looks stay manual (one per landed
increment, walked in commit order; a precision drop reverts that commit), and only surviving
commits are fast-forwarded to `main` by hand. `/mine --smoke` self-tests the pipeline.

## Commands

```
uv run pytest                                            # unit tests (synthetic only)
uv run rulekit --project projects/gsm8k bench --slice suite|dev-train|dev-holdout
uv run rulekit --project projects/gsm8k bench --slice dev-train --snapshot before.json
uv run rulekit --project projects/gsm8k diff before.json after.json    # ship gate
uv run rulekit --project projects/asdiv bench --slice dev --jobs 8      # CROSS-CORPUS gate (§3b) — packs mined only on GSM8K, run on ASDiv
uv run rulekit --project projects/svamp bench --slice dev --jobs 8      # 2nd CROSS-CORPUS gate — SVAMP (adversarial variations, harder)
uv run rulekit --project projects/mawps bench --slice dev --jobs 8      # 3rd — MAWPS (classic arithmetic repository)
uv run rulekit --project projects/scibench bench --slice dev --jobs 8   # 4th — SciBench OUT-OF-DOMAIN safety (want 0 commits)
uv run rulekit --project projects/folio bench --slice dev --jobs 8      # 5th — FOLIO LOGIC safety, the only NON-arithmetic gate (want 0 commits)
uv run rulekit --project projects/gsm8k stats                          # the mining worklists
uv run rulekit --project projects/gsm8k lint [--category NAME]         # overlaps, blast radius
uv run rulekit --project projects/gsm8k serve                          # visual designer
```

## Layout

- `src/rulekit/kernel/` — the frozen general machinery (pipeline, facts, guards, document loop)
- `packs/core-english/` — lexicon, obligations, numbers, base categories (hand-curated)
- `packs/difg-mined/` — vocabulary mined from difg; `quarantine.yaml` lists words difg
  deliberately withheld (holdout poison) — CHECK IT before admitting new vocabulary
- `packs/arithmetic/` — pattern rules, ask shapes, synthesizers (the general solver families)
- `projects/gsm8k/` — the benchmark project (data + snapshots gitignored; suite = curated)
- `projects/asdiv/` — the CROSS-CORPUS precision gate: same packs, DIFFERENT authors' problems, run
  through the same ship gate to catch confident-wrongs GSM8K structurally can't see (methodology §3b).
  `build_corpus.py` (committed) defines the DEV/TEST firewall; data gitignored, rebuild once with
  `uv run --with datasets python projects/asdiv/build_corpus.py`
- `projects/svamp/`, `projects/mawps/`, `projects/scibench/` — the 2nd–4th cross-corpus gates. SVAMP
  (adversarial variations, harshest in-domain), MAWPS (classic arithmetic repository), and SciBench
  (out-of-domain college science — an over-commitment/safety check, expected 0 commits). Same shape as
  asdiv; each rebuilt once with `uv run --with datasets python projects/<name>/build_corpus.py`
- `projects/folio/` — the 5th and only NON-ARITHMETIC gate: human-written first-order logic (Yale-LILY).
  Every other gate asks for a number, so none can catch the engine ASSERTING a number at logic prose;
  a committed number against its verdict/text golds scores WRONG. Expect 0 commits. Its firewall buckets
  by PREMISE BLOCK, not per-item (340 stories → 1,001 items), and its 'Uncertain' gold is `text`, never
  `decline` — see `docs/negative-results.md` → "The logic-corpus search" before touching either.

Mining scripts are throwaway: keep them in the session scratchpad, never the repo — recreate
from `docs/methodology.md` §4.
