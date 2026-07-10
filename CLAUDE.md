# rulekit

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

## Commands

```
uv run pytest                                            # unit tests (synthetic only)
uv run rulekit --project projects/gsm8k bench --slice suite|dev-train|dev-holdout
uv run rulekit --project projects/gsm8k bench --slice dev-train --snapshot before.json
uv run rulekit --project projects/gsm8k diff before.json after.json    # ship gate
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

Mining scripts are throwaway: keep them in the session scratchpad, never the repo — recreate
from `docs/methodology.md` §4.
