---
name: mine
description: Run one GSM8K mining batch — scout candidates, implement them in parallel Sonnet worktrees under the full dev gate, constitution-review each diff, integrate sequentially onto a staging branch. Stops before TEST; never merges main.
argument-hint: "[count] [--smoke]"
---

# /mine — one automated mining batch

Runs the mining methodology as a multi-agent pipeline:
**Scout** (session model) selects candidate increments from fresh
`rulekit stats` + the HANDOFF worklist → **parallel junior implementers**
(Sonnet) each build one candidate in an isolated git worktree through the full
dev gate → **constitution reviewer** (session model) checks each gated branch
diff for lexicon-in-Python / one-off-parsing / GSM8K-in-tests / quarantine
violations → **integrator** (Sonnet) lands review-passed candidates one at a
time onto `mining/batch-<date>`, re-running the FULL dev gate on the
integrated state after each pick (parallel dev gates don't compose).

The pipeline STOPS at the staging branch. It never merges or fast-forwards
`main`, never runs `--slice test`, never spends a TEST look.

## Arguments

- `count` — number of candidates to scout (default **5**).
- `--smoke` — pipeline self-test: skips the scout, runs one injected no-op
  candidate (YAML comment + trivial synthetic test, diff-NEUTRAL) through
  every stage, then all branches are deleted in cleanup. Use after changing
  the pipeline itself.

## Protocol for the main agent

### 1. Preflight (you have Bash; the workflow does not)

Abort with a clear message if any of these fail:

- `git -C <repo> status --porcelain` is empty (clean tree) and the current
  branch is `main`.
- `git -C <repo> worktree prune`, then warn (don't abort) if
  `git branch --list 'mining/*'` shows leftovers from a previous batch —
  ask nothing, just report them; stale `mining/cand-*` branches from a
  crashed run should be surfaced to the user before piling on more.
- Quick sanity: `uv run rulekit --project projects/gsm8k bench --slice suite`
  → `correct 52`, `wrong 0`.

### 2. Run the workflow

Invoke the Workflow tool with `scriptPath: .claude/workflows/mine.js` and
args (actual JSON values, not a string):

```
{ "count": <count>, "smoke": <bool>, "date": "<today YYYY-MM-DD>",
  "repo": "<absolute repo path>", "wtRoot": "<absolute repo path>-worktrees" }
```

Do NOT hand-implement the phases inline in the conversation, and do not
"help" a struggling subagent by editing its worktree from the main session.

### 3. Cleanup (after the workflow returns)

- Remove candidate worktrees (branches survive):
  `git worktree remove --force <wtRoot>/<slug>` for each candidate, then
  `git worktree prune`. Keep the staging worktree if increments landed
  (the user spends TEST looks from it); remove it too if nothing landed.
- Smoke run: additionally delete `mining/batch-<date>` and
  `mining/cand-smoke-noop`, remove the staging worktree, then verify
  `git branch --list 'mining/*'` is empty, `git worktree list` is clean, and
  the main checkout's `projects/gsm8k/snapshots/` (incl. `test-ledger.jsonl`)
  is untouched. Report PASS/FAIL per stage.

### 4. Report

Present: a landed table (increment N, class, commit), deferred table (slug,
phase, reason), failed table (slug, `[FAILED-GATE]` branch for postmortem),
and the staging branch name. Then the exact manual steps:

```
# per landed increment, in order (one TEST look each — methodology step 8):
git checkout mining/batch-<date> && git checkout <commit-of-increment-N>
uv run rulekit --project projects/gsm8k bench --slice test --spend-test-look
# precision holds vs last look -> keep; drops -> revert that commit (methodology §8)
# after walking all increments: fast-forward main past the survivors and push
```

Suggest (don't do): durable lessons from failed candidates belong in
`docs/negative-results.md`; deferred briefs go back to the HANDOFF worklist.

## Hard rules (enforce even if a subagent drifts)

- TEST looks are the user's budget, spent manually, ONE per landed increment,
  walking the linear staging commits in order. A TEST precision drop reverts
  that increment's commit — no matter how good DEV looked.
- Never merge to `main` from this pipeline; never `--spend-test-look`.
- Mining scripts are throwaway scratchpad files (methodology §4) — if any got
  committed, that's a review failure to report.
