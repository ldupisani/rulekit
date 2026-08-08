---
name: mine
description: Run or resume one GSM8K Mining v2 batch with generated evidence, Designer human review, exact machine gates, constitution review, and sequential integration. Stops before protected TEST and never merges main.
argument-hint: "[count] [--smoke] [--integrate-approved]"
---

# /mine — GSM8K Mining v2

This is the Codex-native orchestrator. Agent behavior lives only in
`.agents/protocols/`; `.codex/agents/*.toml` are thin launch adapters. Read
`AGENTS.md`, `.agents/protocols/standing-gate.md`, and the active Mining v2 plan
before starting.

Agent registrations are loaded when a Codex task starts. If a long-running
task still advertises an old role description (especially a scout mentioning
DIFG), do not launch that stale role. Launch a default subagent with an
explicit first instruction to read the matching canonical protocol instead.
The files, not session-cached role metadata, are authoritative.

The workflow has a deliberate human pause:

```text
scout → parallel implementation → constitution review → publish manifests
      → STOP for Designer review + exact machine gate
      → /mine --integrate-approved → sequential integration → STOP before TEST
```

## Arguments

- `count`: candidate briefs to scout, default 2.
- `--smoke`: one no-op candidate that exercises the same manifest, review,
  machine-gate, and integration seams. It may claim `class_evidence.mode=smoke`
  but receives no other gate exemption.
- `--integrate-approved`: resume the current batch using only exact approved,
  machine-passed queue records. Do not scout or implement.

## Preflight

Before either path:

1. Require the main checkout on `main` with no source/doc changes. Project-local
   generation and campaign ledgers may be dirty because they are append-only
   human evidence; report them, never stage or discard them.
2. Prune worktree metadata and report leftover `mining/*` branches/worktrees.
3. Run curated suite and require all emitted items correct, without comparing
   to a historical count.
4. Never stop or restart the user's Designer server.

## New batch

An explicitly user-chosen product-led manual class may enter at step 2 without
an automatic scout only when its `class_evidence.mode` is `product`. It must
claim zero corpus pool/yield, carry the user's product rationale, and receive
the same complete implementation, generated evidence, constitution review,
human review, machine gate, and sequential integration as a coverage
candidate. Never infer product selection from a failed scout; the user must
choose it.

1. Spawn one `mining-scout` agent with the requested count, exact base commit,
   main/worktree paths, and a JSON output request matching its canonical
   protocol. For `--smoke`, inject the no-op brief instead.
2. Validate briefs locally against `CampaignClassEvidence`,
   `CampaignGenerationContract`, and `CampaignImplementationContract`. Drop a
   malformed, overlapping, zero-yield, or known-negative brief before spending
   an implementer.
3. Spawn one `mining-implementer` per accepted brief in parallel. Assign each
   exact worktree, branch, files/classes it owns, and uncommitted manifest path.
   State that workers are not alone and must never revert one another.
4. For every `gated` result, spawn a `constitution-reviewer`. Failed/deferred
   branches remain for postmortem and are never published. Attach the passing
   structured verdict as `constitution_review` in the uncommitted manifest;
   never alter captured candidate evidence.
5. Validate every review-passed manifest with the central checkout, then publish
   it using:

   `rulekit --project projects/curated campaign-publish <manifest-path>`

6. Stop. Report published candidates and tell the user to open Campaign in the
   existing Designer, inspect all specimens, record a decision, and run the
   exact machine gate. Do not poll for human approval and do not integrate yet.

## Resume approved

1. Read `rulekit --project projects/curated campaign-queue`. Select only latest
   revisions whose human status is `approved` and whose exact machine gate is
   present and passing, and which have no exact `landing` record. Landed,
   stale, missing, or failed evidence remains deferred.
2. Spawn one `mining-integrator` in setup mode for the batch staging worktree.
3. Send approved candidates to that same integrator one at a time in priority
   order. After each final result, send the next; never parallelize integration.
4. After each green integrator result, append an exact central landing with
   `rulekit --project projects/curated campaign-land <landing-json>`. Pin the
   manifest commit/fingerprint, latest approval id, latest passing gate id,
   staging branch/commit, and assigned increment. Stop if that durable record
   is rejected; never send the next candidate first.
5. Stop at `mining/batch-<date>`. Never merge/fast-forward main, push, or run a
   protected slice.
6. Report landed/deferred/failed candidates, staging branch and commits, plus
   the manual main-checkout TEST walk from `docs/methodology.md`. The user owns
   every protected look and subsequent promotion to main.

## Cleanup

Do not remove a published candidate worktree while it may still be reviewed in
the Designer. After integration or explicit deferral, stop only that owned
candidate runner if necessary, remove its worktree, and prune. Never touch an
unrelated running server. A smoke branch is removed only after its full resumed
path succeeds and its protected-file hashes remain unchanged.

## Hard rules

- No TEST/generalization or protected-item inspection.
- No automatic approval, integration before human approval, main merge, or push.
- No inline implementation from the root agent; candidate code belongs to its
  assigned implementer worktree.
- No historical suite/test count in workflow logic.
- No manifest without canonical traces for every required specimen.
- No integration without constitution pass + exact human approval + exact
  passing machine gate.
- No second integration of an exact revision that already has a landing.
- No benchmark-yield claim on an explicitly product-led manual candidate.
