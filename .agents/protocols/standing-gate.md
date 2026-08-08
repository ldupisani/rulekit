# Mining v2 standing gate — canonical protocol

This file is the single source of truth for every mining agent. Read
`AGENTS.md`, `docs/gsm8k-mining-v2-plan.md`, `docs/methodology.md`, and
`docs/HANDOFF.md` before using it.

## Firewall

- Inspect and tune only GSM8K `dev-train`.
- `dev-holdout` is an opaque delta gate. Never inspect its items to tune.
- Never run `test`, `generalization`, `--spend-test-look`, or read a protected
  parquet/ledger. Protected looks remain manual after integration.
- Never copy a benchmark sentence into tests, manifests, briefs, logs, or
  documentation. Item ids and structural paraphrases are sufficient evidence.

## Exact candidate gate

The Designer's machine gate is authoritative. It derives fresh snapshots from
the clean central `HEAD` and exact clean candidate commit for:

- curated `suite`;
- GSM8K `dev-train` and `dev-holdout`;
- ASDiv, SVAMP, MAWPS, SciBench, DIFG, and FOLIO `dev`;
- COGS `dev-train` and `dev-holdout`; and
- PMB `train` and `development`.

It also runs `pytest -q -n 4 --dist=worksteal`, curated lint, FOLIO's zero
numeric-commitment assertion, canonical trace/review replay, and protected-file
byte-integrity checks. Pass means zero BROKE/DECL→WRONG, no incorrect graph,
curated all-correct using the emitted item count, and every synthetic check
green. Never substitute a hand-written subset.

## Candidate manifest

Every non-smoke candidate publishes `rulekit/campaign-review@2` evidence:

- one named general class and its DEV pool/yield claim;
- walked DEV item ids and structural paraphrases, never corpus prose;
- premise-side and ask-side mechanisms, including which side already exists;
- exact bounded vocabulary admissions, quarantine result, and collision risk;
- a passing read-only constitution verdict attached after implementation;
- expected files, synthetic-only test modules, and class justification;
- premise/ask targets and required specimen kinds;
- strict-positive, controlled-boundary, complete-answerable, and deliberate-
  decline specimens (unless the explicit generation contract marks a smaller
  applicable set);
- canonical trace evidence for matches/bindings, facts, collisions,
  deficiencies, ask, answer/clarification, and proof; and
- explicit ordinary review ids where earlier human evidence is relevant.

Manifests are uncommitted orchestration evidence. Publish them centrally with
`rulekit --project <central-project> campaign-publish <manifest.json>`; never
commit them on the candidate branch.

## Promotion order

Implementation may run in parallel. Constitution review may follow each
completed implementation. Everything after that is sequential:

1. publish immutable manifest;
2. human review in the central Designer;
3. exact machine gate in the central Designer;
4. require an exact approved decision and exact passing gate;
5. integrate one candidate;
6. re-run the exact standing gate on the integrated state before considering
   the next candidate.

No approval, stale approval, stale gate, review request, or unclear decision
is landable.
