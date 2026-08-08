# GSM8K Mining v2 integrator — canonical protocol

Operate only in the supplied staging worktree. Never write main, merge main,
push, or touch protected slices. Read `AGENTS.md` and the standing-gate
protocol first.

## Setup

Create a clean `mining/batch-<date>` staging branch from the supplied exact
base with its own `.venv`, read-only DEV data links, and local snapshots. Build
fresh standing snapshots and run the parallel full suite.

## Land one candidate

The orchestrator must supply the candidate's exact central queue record. Refuse
unless constitution verdict is pass, the latest human decision is `approved`,
the latest machine gate passes, and decision/gate/manifest all match the exact
candidate id, commit, and registry fingerprint.

Cherry-pick only the reviewed candidate delta. On conflict, abort and defer;
never hand-resolve. Run the full standing gate against current staging
baselines. Any BROKE, DECL→WRONG, incorrect projection, FOLIO numeric
commitment, lint error, test failure, protected digest change, or specimen/
review replay change defers the candidate and restores the pre-pick state.

Finalize by assigning the next synthetic increment test number and recording a
short mining-log entry. Do not append campaign narratives to HANDOFF. Squash
the pick/finalization into one commit and advance every baseline snapshot only
after proving no runtime files changed after measurement.

Return JSON `{status,increment,commit,gate_evidence,summary,notes}` with status
`landed|deferred`. Integration is strictly sequential; the next candidate may
start only after this result is final and the orchestrator has recorded the
successful result in the central landing ledger. The staging integrator never
writes that central ledger itself.
