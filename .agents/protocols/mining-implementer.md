# GSM8K Mining v2 implementer — canonical protocol

Own exactly one candidate worktree and branch. You are not alone in the
codebase: do not revert another worker's edits, do not touch main, and adjust
only your assigned class/files. Read `AGENTS.md`, the standing-gate protocol,
HANDOFF invariants, methodology, and the supplied brief before editing.

## Worktree and baseline

Create `mining/cand-<slug>` from the supplied exact base. The worktree must
have its own `.venv`; never share main's editable environment. Symlink every
required gitignored DEV data directory read-only from main, but create local
empty snapshot directories. Verify exact HEAD and clean status.

Before editing, emit baseline snapshots for the complete standing DEV matrix
and record the parallel full-test result. Never inspect holdout items.

## Implementation

- Implement the one class YAML-first. Python may add general machinery, never
  word lists or problem-specific parsing.
- Stay inside `implementation_contract.files_expected` unless a discovered
  adjacent file is necessary and explicitly reported as scope drift.
- Add the declared synthetic-only tests, including a valid neighbor and a
  decline-safety boundary. Invent every name, number, and object from scratch.
- Run those synthetic tests before consulting the selected item as an
  acceptance check. After they pass, reload the original DEV-train item from
  the local corpus by its supplied id and require an exact correct result.
  Never paste its prose into source, tests, the manifest, or command output.
- Treat missing ordinary vocabulary as part of the vertical increment: add
  bounded senses, morphology, and semantic categories in YAML, with quarantine
  and collision checks, rather than leaving the item artificially unread.
- After at most twenty root-cause repair cycles, return a clean failure rather
  than weakening a gate.

## Evidence and output

Run the complete standing gate from `.agents/protocols/standing-gate.md` using
fresh baseline/candidate snapshots. Commit only intended source/pack/test
files by named path. Never commit generated snapshots, data links, scripts,
manifest evidence, or campaign ledgers.

Create an uncommitted manifest JSON at the exact path supplied by the launch
prompt. It must validate as `CampaignCandidateManifest`, use the committed
HEAD, name the exact `runtime_project` whose registry loads every candidate
pack, use that same loaded registry fingerprint, and carry canonical trace
evidence for every required specimen. The central campaign project stores the
evidence; it does not implicitly define the candidate runtime. Capture traces
by loading the declared worktree project and calling `rulekit --project
<candidate-project> campaign-trace <text>` (plus an
explicit interpretation/reference year when required). This command reuses the
ordinary Designer trace path; do not synthesize expected facts by hand. Leave
`constitution_review` null for the read-only reviewer/orchestrator to attach. A
manifest without all required traces is a failed implementation.

Return JSON `{candidate,status,branch,commit,files_touched,manifest_path,
gate_evidence,summary,notes}` with status `gated|failed|deferred`.

Forbidden: TEST/generalization, main writes, pushes, copied corpus strings,
shared `.venv`, broad staging commands, committed scratch scripts, or editing
the brief to make the result appear compliant.
