# Session handoff — 2026-07-11

Read this + `CLAUDE.md` (the constitution) + `docs/methodology.md` before touching anything.
State below is committed and pushed through `1c6453f` on `main` (github.com/ldupisani/rulekit).

## Where the project is

Everything through P5 of the original plan is DONE: kernel, YAML packs, lint
(overlap witnesses + blast radius), document re-parse loop, GSM8K harness with
firewall, visual designer (`rulekit serve`, port 8321 — busy-state, slice
targets, TEST gated behind a checkbox). The GSM8K mining campaign is in full
swing under the constitution (no lexicon in Python, no per-problem parsing,
every increment through the gates).

**Current numbers (all verified at head):**
- dev-train: 13 correct / 0 wrong (3,772 items, 100% precision)
- dev-holdout: 12 correct / 0 wrong (3,701 items)
- curated suite: 52/52 · pytest: 112 · lint: 0 errors, 1 intended warning
- TEST ledger (7 looks spent, `projects/gsm8k/snapshots/test-ledger.jsonl`):
  0/1 (0%) → 4/1 (80%) → 5/1 (83.3%) → 5/2 REVERTED → 5/1 → 5/2 bisect → **5/1 (83.3%) ← live**
- The 1 persistent TEST wrong is a stable §3a unseen shape, present since look #1.

## The mining loop (how work ships)

1. Baselines live in `projects/gsm8k/snapshots/` — the CURRENT baselines are
   `narrow2-train.json` / `narrow2-holdout.json` (identical to head behavior).
2. Mine with throwaway scripts in the session scratchpad (never the repo):
   bucket `solve()` decline reasons over dev-train; `rulekit stats` also works.
3. Build the tightest GENERAL mechanism (YAML rules/categories first; kernel
   only for structure). One class per increment, named at ship time.
4. Gate: `bench --slice dev-train --snapshot X.json` → `diff <baseline> X.json`
   (must be 0 BROKE / 0 DECL→WRONG) → same for dev-holdout → synthetic pytest
   (never GSM8K strings) → suite must hold 52/52.
5. TEST look per shipped increment: `bench --slice test --spend-test-look`.
   Precision must hold vs the last look (83.3%) or the increment REVERTS
   (this happened — see docs/negative-results.md; the protocol works).

## Re-landing plan remainder (docs/negative-results.md)

The rate-machinery revert is RESOLVED — culprit was accounting-by-existence,
now fixed (a Rate's value counts as read only when the arithmetic log used
it). Ask-specificity ordering and the narrow rate-span committer are LIVE.
Still parked in git history at `2d7b90c`, each needing its own look:
1. conversion spans ("10 meters a minute … in 2 hours" — lift the
   span_unit != rate.per decline in answer.py's rate-span consumer)
2. rate × population ("a bird eats 7 berries a day, Samuel has 5 birds" —
   lift the population decline; the reverted implementation summed
   _entity_total per holder of the rate's entity-kind)
3. the `entity` slot type (factory-style common-noun ask subjects)

## The next mining worklist (from the last close-miss scan)

- ~500 rate/price compositions (many now decline WITH the rate read — the
  remaining blockers are the three parked pieces above plus price-per-item
  "2 quiches for $15.00 each" forms)
- ~210 "no quantity known": partitions ("Ten OF THEM are yellow"), goal/
  deficit shapes ("goal is 30 situps … make up the rest")
- ~70 fold-vs-fold conflicts: possessed-noun entity identity (Kennedy's
  house vs Benedict's house both lemma 'house' — needs attr-qualified
  entities; also blocks "coconut trees vs mango trees" noun-standard
  relations, attr-blind measure matching generally)
- 153-ish questions with embedded when/after clauses (only "If…," splits)
- noun-antecedent pronouns ("it" → the bear; needs animacy data in packs)

## Hard-won invariants (do not relearn these)

- Every new FACT KIND must decide explicitly whether existence or USE
  constitutes "read" for value accounting (the look #4–#7 lesson).
- Polarity/stateness/plurality are DATA (categories: acquire/lose ±1,
  state, produce/receive +1; lexicon `number:` field). An untagged event
  verb declines the fold — tag it in difg-mined members, never default +1.
- All state verbs (have/own/be) are ONE equivalence class for relation
  resolution blocking; relations carry the sentence's verb.
- Fractions/rest resolve strictly in sentence order (out-of-order = self-
  collision); pools = signed sum of prior-sentence facts, synth/rest excluded.
- Name merging: only single capitalized WORDS join names; merged units never do.
- Asks match by specificity (max consumed units); ask templates referencing
  unbound optional slots omit the key; only {slot.value} slots count as
  consumed by an ask.
- The one lint warning (fraction-of-remnant shadows fraction-of-pool) is
  intended subsumption documentation, not a problem.
- `check packs/difg-mined/quarantine.yaml` before admitting new vocabulary.
- The 'world' entity (bare existentials) and `measure: currency` (category
  name in ask data, resolved against facts) are pack-owned data constants.

## Quick commands

```
uv run pytest -q
uv run rulekit --project projects/gsm8k bench --slice suite|dev-train|dev-holdout [--snapshot F]
uv run rulekit --project projects/gsm8k diff narrow2-train.json <new>.json
uv run rulekit --project projects/gsm8k stats
uv run rulekit --project projects/gsm8k serve         # designer :8321
uv run rulekit --project projects/gsm8k bench --slice test --spend-test-look   # DELIBERATE
```

Auto-memory (`~/.claude/projects/-Users-louis-Development-rulekit/memory/`)
carries the same state in condensed form and is loaded automatically.
