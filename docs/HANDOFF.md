# RuleKit handoff

**Updated:** 2026-10-02

**Code checkpoint:** `8a73704`, committed and pushed to `origin/main`.

**Default workflow:** direct implementation of supplied questions; mining
only when explicitly requested.

This is the operational entry point, not a development history. The complete
previous handoff is preserved in
[HANDOFF-archive-2026-10-02.md](HANDOFF-archive-2026-10-02.md).
Check Git status before starting: this checkpoint does not imply a future
checkout is clean.

## Read as needed

- [CLAUDE.md](../CLAUDE.md): constitution, workflow, commands and validation policy.
- [Architecture](architecture.md): application boundaries and data flow.
- [YAML reference](yaml-reference.md): pack/project syntax, category relationships,
  templates, generation contracts and authoring guidance.
- [Methodology](methodology.md): DEV/TEST firewall; read before benchmark work.
- [Generation plan](generation-and-annotation-plan.md): Designer product contract.
- [Mining plan](gsm8k-mining-v2-plan.md) and [mining log](mining-log.md):
  explicit campaign procedure and landed/protected checkpoints.

## Current implementation

The pushed checkpoint includes:

- **Ordered batch outcomes:** per-batch fractions, complete-population checks,
  and positive/complement asks. Reuses typed evidence and shared accounting;
  incomplete, overlapping or incompatible batches decline.
  [Invented examples](batch-outcome-examples.md).
- **Nominal role families:** noun-only category `includes` unions replace
  duplicated holder/actor lists. Grammar maps roles; category data owns
  compatibility. Inclusion does not import behavioral flags or imply events,
  affiliations, or personal-pronoun eligibility.
- **Documentation and Designer help:** architecture and YAML authoring are
  separate. The editor's YAML reference link opens local help and live schemas;
  installed wheels bundle the same authored Markdown files.

The existing Designer was not restarted during this work. A user-managed
restart is needed if it still runs the older Python/schema version. Do not
interrupt an active reviewer automatically.

## Validation at this checkpoint

These are recorded results, not a claim that every gate was rerun on the
final commit:

| Check | Latest recorded result |
| --- | --- |
| Pre-commit batch/category/docs/server tests | 145 passed |
| Final role-audit affected-file rerun | 343 passed |
| Curated suite | 71 correct, 0 wrong |
| GSM8K DEV-train / DEV-holdout | 120 / 58 correct, 0 wrong |
| ASDiv DEV | 55 correct, 0 wrong |
| Final role-audit DEV comparisons | 0 BROKE, 0 DECL→WRONG |
| Curated / GSM8K lint | 0 errors; 2 / 3 existing warnings |
| Documentation | Examples and links checked; wheel contents and browser rendering verified |

The broad role-audit run had 9,226 passes and two stale expectations, both
repaired and covered by the 343-test rerun. That broad run preceded the final
person/holder hierarchy refinement; there is **no fresh uninterrupted
full-suite pass for the final state**. Use the normal risk-based checks when
making the next change, not older full-suite totals as current evidence.
Detailed logs and earlier checkpoints are indexed in the archive;
`/tmp/rulekit-role-audit.ckA1iL/` is temporary local evidence, not a durable
repository artifact.

The last recorded protected GSM8K checkpoint is **increment 134, TEST look
136**: 12 correct, 0 wrong, 1,307 declined, 0 errors. See the
[mining log](mining-log.md). This supersedes the older look-126 summary in the
archive; it does not measure subsequent direct implementations. No new
protected look is authorized by this handoff.

## Working boundaries

The constitution and full procedures live in `CLAUDE.md`; do not duplicate
them here. In particular:

- A supplied GSM8K-style question is ordinary product work, not implicit
  permission for Mining v2 or a protected benchmark look.
- Generation and reviews are authoring evidence only. They never become
  runtime facts or hidden plausibility filters.
- Preserve review history. Corrections, resolutions and tombstones are
  append-only; do not tombstone a user's review merely because code was fixed.
  A valid review with defects is not clean reusable evidence.
- When consolidating categories, keep independent facets, negative exclusions
  and construction-dependent role mappings explicit. Do not force them into
  an inaccurate hierarchy or discard identity, scope or temporal evidence.
- Candidate worktree names are not promotion state. For explicit mining,
  inspect the live queue and landing records and require exact reviewed/gated
  revisions; an old handoff's queue count is not authoritative.
- Committing, pushing, protected looks and a Designer restart require their
  own user authorization.

## Next action

No implementation is currently in flight. Take the next user-supplied
question, premise/ask review batch, or consolidation request through the direct workflow.
Use invented analogues and decline boundaries, then focused tests, curated
regression and relevant lint; broaden checks for shared-kernel changes.
Prefer existing facts, category relationships, templates and consumers.

For an explicit mining request, follow the mining plan and current agent
protocols, ending at the applicable human-review gate. Do not resume a
campaign simply because historical worktrees or plans exist.

## Parked work

**Semantic projection remains parked; Phase E is blocked.** The PMB protected
standard-test look produced 1 exact and 0 incorrect but did not establish the
required independent role classes. The external synthetic candidate at
`/Users/louis/Development/semantic-generator` remains a separate review and
sealing concern. Do not inspect protected COGS/PMB rows, tune against that
aggregate, seal the candidate, or build an importer without explicit campaign
resumption. Then follow the [projection plan](semantic-projection-plan.md) and
[OOD gate plan](semantic-projection-ood-gate-plan.md), verifying licence/release
boundaries and preregistering import and thresholds first.

Other history: [negative results](negative-results.md),
[parked physics campaign](parked-physics-campaign.md), and handoff archives
from [July 23](HANDOFF-archive-2026-07-23.md) and
[July 16](HANDOFF-archive-2026-07-16.md).

Keep this file limited to current state, validation caveats, active boundaries,
and the next action. Put implementation narratives in focused docs or logs.
