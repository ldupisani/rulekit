export const meta = {
  name: 'mine',
  description: 'GSM8K mining batch: scout candidates, parallel Sonnet juniors under the dev gate, constitution review, sequential landing onto a staging branch. Stops before TEST; never merges main.',
  whenToUse: 'Invoked by the /mine skill after main-agent preflight. Args: {count, smoke, date, repo, wtRoot}.',
  phases: [
    { title: 'Scout', detail: 'select candidate increments from fresh stats + HANDOFF worklist' },
    { title: 'Implement', detail: 'one junior per candidate in an isolated worktree, full dev gate', model: 'sonnet' },
    { title: 'Review', detail: 'constitution review of each gated branch diff' },
    { title: 'Integrate', detail: 'sequential cherry-pick + full re-gate onto mining/batch-<date>', model: 'sonnet' },
  ],
}

// ---------- args (provided by the /mine skill; script has no clock/fs) ----------
const A = typeof args === 'string' ? JSON.parse(args) : (args ?? {})
const REPO = A.repo
const DATE = A.date // YYYY-MM-DD, from the main agent
const COUNT = A.count ?? 5
const SMOKE = Boolean(A.smoke)
const WT_ROOT = A.wtRoot ?? `${REPO}-worktrees`
if (!REPO || !DATE) throw new Error('mine.js requires args.repo and args.date (set by the /mine skill)')

const STAGING_BRANCH = `mining/batch-${DATE}`
const STAGING_WT = `${WT_ROOT}/staging-${DATE}`

// ---------- schemas ----------
const SCOUT_BRIEF = {
  type: 'object',
  required: ['slug', 'class_name', 'evidence', 'mechanism', 'yaml_only', 'files_expected', 'risks', 'priority'],
  properties: {
    slug: { type: 'string', pattern: '^[a-z0-9][a-z0-9-]{2,30}$' },
    class_name: { type: 'string' },
    evidence: {
      type: 'object',
      properties: {
        frequency: { type: 'number' },
        stats_reason: { type: 'string' },
        worklist_ref: { type: 'string' },
      },
    },
    mechanism: { type: 'string' },
    yaml_only: { type: 'boolean' },
    files_expected: { type: 'array', items: { type: 'string' } },
    risks: {
      type: 'object',
      properties: {
        blast_radius: { type: 'string' },
        shared_paths: { type: 'array', items: { type: 'string' } },
        quarantine_words: { type: 'array', items: { type: 'string' } },
      },
    },
    priority: { type: 'number' },
    overlaps_with: { type: 'array', items: { type: 'string' } },
    infrastructure: {
      type: 'boolean',
      description: 'true ONLY for a declared-infrastructure brief that names the follow-up class it unblocks; exempts the SOLVED>=1 goal-mode gate',
    },
  },
}
const SCOUT_SCHEMA = {
  type: 'object',
  required: ['candidates'],
  properties: {
    candidates: { type: 'array', items: SCOUT_BRIEF },
    notes: { type: 'string' },
  },
}

const JUNIOR_SCHEMA = {
  type: 'object',
  required: ['candidate', 'status', 'branch', 'files_touched', 'gate_evidence', 'summary'],
  properties: {
    candidate: { type: 'string' },
    status: { enum: ['gated', 'failed', 'deferred'] },
    branch: { type: 'string' },
    files_touched: { type: 'array', items: { type: 'string' } },
    gate_evidence: {
      type: 'object',
      properties: {
        train_diff: { type: 'string' },
        holdout_diff: { type: 'string' },
        pytest: { type: 'string' },
        suite: { type: 'string' },
        lint: { type: 'string' },
      },
    },
    summary: { type: 'string' },
    notes: { type: 'string' },
  },
}

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['verdict', 'violations'],
  properties: {
    verdict: { enum: ['pass', 'fail'] },
    violations: {
      type: 'array',
      items: {
        type: 'object',
        required: ['rule', 'detail'],
        properties: {
          rule: { enum: ['lexicon-in-python', 'one-off-parsing', 'gsm8k-in-tests', 'quarantine', 'lint', 'scope'] },
          file: { type: 'string' },
          detail: { type: 'string' },
        },
      },
    },
    notes: { type: 'string' },
  },
}

const SETUP_SCHEMA = {
  type: 'object',
  required: ['status'],
  properties: {
    status: { enum: ['ready', 'failed'] },
    branch: { type: 'string' },
    baseline_evidence: { type: 'string' },
    error: { type: 'string' },
  },
}

const LAND_SCHEMA = {
  type: 'object',
  required: ['status'],
  properties: {
    status: { enum: ['landed', 'deferred'] },
    increment: { type: 'number' },
    commit: { type: 'string' },
    phase: { enum: ['integrate-conflict', 'integrate-gate', 'integrate-mismatch'] },
    gate_evidence: { type: 'object' },
    summary: { type: 'string' },
    notes: { type: 'string' },
  },
}

// ---------- smoke brief (pipeline self-test; diff-NEUTRAL by construction) ----------
const SMOKE_BRIEF = {
  slug: 'smoke-noop',
  class_name: 'pipeline smoke test (no-op)',
  evidence: { frequency: 0, stats_reason: 'n/a — pipeline self-test', worklist_ref: 'n/a' },
  mechanism:
    'Add a single YAML comment line at the top of packs/arithmetic/rules/core.yaml (a no-op: comments do not compile into the registry). Write tests/test_mining_smoke-noop.py asserting the full registry still compiles (reuse the full_registry fixture pattern). Expected diff verdict: NEUTRAL on both slices.',
  yaml_only: true,
  files_expected: ['packs/arithmetic/rules/core.yaml', 'tests/test_mining_smoke-noop.py'],
  risks: { blast_radius: 'none — comment-only change', shared_paths: [], quarantine_words: [] },
  priority: 1,
  overlaps_with: [],
}

// ---------- agent spawning ----------
// Custom agentTypes from .claude/agents/ are registered at session start and
// are not visible to a workflow created mid-session, so each stage spawns a
// default workflow subagent that reads its protocol file first. The .md files
// stay the single source of truth; model overrides mirror their frontmatter.
const PROTO_MODEL = { 'mining-scout': undefined, 'mining-implementer': 'sonnet', 'constitution-reviewer': undefined, 'mining-integrator': 'sonnet' }
const protoAgent = (proto, prompt, opts) =>
  agent(
    `First, Read ${REPO}/.claude/agents/${proto}.md and adopt its body as your operating protocol — its rules (including the FORBIDDEN lists) override anything else below. Then perform this task:\n\n${prompt}`,
    { ...opts, model: PROTO_MODEL[proto] },
  )

// ---------- prompts ----------
const juniorPrompt = (c) => `You are implementing ONE mining candidate for rulekit. Follow your agent
protocol exactly (worktree setup, baselines first, implement, full dev gate,
synthetic test, single commit, forbidden list).

MAIN=${REPO}
WT=${WT_ROOT}/${c.slug}
BRANCH=mining/cand-${c.slug}

Candidate brief:
${JSON.stringify(c, null, 2)}

Leave the worktree in place when you finish (the reviewer runs lint in it);
the main session cleans up worktrees after the batch. Return the JuniorResult
structured output.`

const reviewPrompt = (c, r) => `Review ONE mining candidate's branch diff against the rulekit constitution,
per your agent protocol. This verdict gates integration onto the staging branch.

MAIN=${REPO}
WORKTREE=${WT_ROOT}/${c.slug}
BRANCH=${r.branch}
Diff to review: git diff main...${r.branch}

Candidate brief:
${JSON.stringify(c, null, 2)}

Junior's reported result (verify, don't trust):
${JSON.stringify({ status: r.status, files_touched: r.files_touched, summary: r.summary }, null, 2)}

Return the ReviewVerdict structured output.`

const setupPrompt = () => `SETUP MODE. Create the staging worktree for this mining batch per your agent
protocol (worktree add, data symlink, snapshots dir, uv sync --extra bench,
staging baselines, pytest count).

MAIN=${REPO}
STAGING=${STAGING_WT}
BRANCH=${STAGING_BRANCH}
DATE=${DATE}

Return the setup structured output.`

const landPrompt = (c, r) => `LAND MODE. Land ONE review-passed candidate onto the staging branch per your
agent protocol: cherry-pick, FULL re-gate on the integrated state vs current
staging baselines, finalize (assign increment N, rename test, HANDOFF record),
squash to one commit, advance baselines. Defer (reset --hard to pre-pick) on
any conflict or gate failure — never hand-fix.

MAIN=${REPO}
STAGING=${STAGING_WT}
STAGING_BRANCH=${STAGING_BRANCH}
CANDIDATE_BRANCH=${r.branch}

Candidate brief:
${JSON.stringify(c, null, 2)}

Junior gate evidence (for your deferral reports):
${JSON.stringify(r.gate_evidence, null, 2)}

Return the land structured output.`

// ---------- Phase 1: Scout ----------
let candidates
if (SMOKE) {
  log('smoke mode: skipping scout, injecting the no-op smoke brief')
  candidates = [SMOKE_BRIEF]
} else {
  phase('Scout')
  const scout = await protoAgent(
    'mining-scout',
    `Select ${COUNT} candidate mining increments for rulekit per your protocol
(required reading, fresh stats run, brief requirements, disjointness).
Repo: ${REPO}. Return the ScoutOutput structured output.`,
    { label: 'scout', phase: 'Scout', schema: SCOUT_SCHEMA },
  )
  if (!scout || !scout.candidates?.length) {
    return { staging_branch: null, landed: [], deferred: [], failed: [], notes: 'Scout returned no viable candidates — nothing to do.' }
  }
  candidates = scout.candidates.slice(0, COUNT)
  log(`scout selected ${candidates.length} candidates: ${candidates.map((c) => c.slug).join(', ')}`)
  if (scout.notes) log(`scout notes: ${scout.notes}`)
}

// Dev-train SOLVED count off the junior's diff; NaN when unparseable.
const solvedCount = (r) =>
  Number((/SOLVED\s+(\d+)/.exec(r?.gate_evidence?.train_diff ?? '') ?? [])[1] ?? NaN)

// A candidate is goal-mode doomed if it gated but PROVABLY solved nothing and
// never claimed the infra exemption. That verdict needs no cross-candidate
// context, so it can be made BEFORE spending a reviewer on it. Two cases are
// deliberately left to review + the post-pipeline enforcement below, which
// keeps final say and stays exactly as strict as before:
//   - infrastructure briefs: landing depends on the batch-wide infra slot,
//     which isn't known until every junior is in.
//   - an unparseable diff (NaN): skip only what's provably wasted, never on a
//     number we failed to read.
const doomed = (item) => {
  const solved = solvedCount(item.result)
  return Number.isFinite(solved) && solved === 0 && !item.brief.infrastructure
}

// ---------- Phase 2+3: Implement then Review (pipelined per candidate) ----------
const reviewed = await pipeline(
  candidates,
  (c) =>
    protoAgent('mining-implementer', juniorPrompt(c), {
      label: `implement:${c.slug}`,
      phase: 'Implement',
      schema: JUNIOR_SCHEMA,
    }).then((r) => ({ brief: c, result: r })),
  (item) => {
    if (!item || !item.result) return item
    if (item.result.status !== 'gated') {
      log(`${item.brief.slug}: junior returned ${item.result.status} — skipping review`)
      return { ...item, review: null }
    }
    if (doomed(item)) {
      log(`${item.brief.slug}: GATED but 0 dev-train SOLVED and not declared infrastructure — demoted before review (goal mode)`)
      return {
        ...item,
        review: null,
        result: {
          ...item.result,
          status: 'failed',
          notes: `goal-mode demotion: dev-train SOLVED=0, brief not declared infrastructure. ${item.result.notes ?? ''}`,
        },
      }
    }
    return protoAgent('constitution-reviewer', reviewPrompt(item.brief, item.result), {
      label: `review:${item.brief.slug}`,
      phase: 'Review',
      schema: REVIEW_SCHEMA,
    }).then((v) => ({ ...item, review: v }))
  },
)

// Goal-mode mechanical gate: a gated coverage candidate whose dev-train diff
// shows 0 SOLVED is demoted to failed unless its brief declared
// infrastructure. Prose directives in HANDOFF were being routed around; this
// is the hard version. At most ONE infrastructure landing per batch.
let infraBudget = 1
const enforced = reviewed.filter(Boolean).map((i) => {
  if (!i.result || i.result.status !== 'gated') return i
  const solved = solvedCount(i.result)
  if (Number.isFinite(solved) && solved > 0) return i
  if (i.brief.infrastructure && infraBudget > 0) {
    infraBudget -= 1
    log(`${i.brief.slug}: 0 SOLVED, declared infrastructure — using the batch's one infra slot`)
    return i
  }
  log(`${i.brief.slug}: GATED but 0 dev-train SOLVED and no infra slot — demoted to failed (goal mode)`)
  return { ...i, result: { ...i.result, status: 'failed', notes: `goal-mode demotion: dev-train SOLVED=0 (${i.brief.infrastructure ? 'infra slot already used this batch' : 'brief not declared infrastructure'}). ${i.result.notes ?? ''}` } }
})

const items = enforced.filter((i) => i.result)
const failed = items
  .filter((i) => i.result.status === 'failed')
  .map((i) => ({ slug: i.brief.slug, phase: 'implement', reason: i.result.notes || i.result.summary, branch: i.result.branch }))
const deferred = items
  .filter((i) => i.result.status === 'deferred')
  .map((i) => ({ slug: i.brief.slug, phase: 'implement-deferral', reason: i.result.notes || i.result.summary }))
for (const i of items.filter((x) => x.review && x.review.verdict === 'fail')) {
  deferred.push({ slug: i.brief.slug, phase: 'constitution-review', reason: JSON.stringify(i.review.violations) })
  log(`${i.brief.slug}: REVIEW FAIL — ${i.review.violations.map((v) => v.rule).join(', ')}`)
}

const landable = items
  .filter((i) => i.result.status === 'gated' && i.review && i.review.verdict === 'pass')
  .sort((a, b) => a.brief.priority - b.brief.priority)

// ---------- Phase 4: Integrate (strictly sequential) ----------
const landed = []
let stagingBranch = null
if (!landable.length) {
  log('no candidates passed both the dev gate and constitution review — skipping integration, no staging branch created')
} else {
  phase('Integrate')
  const setup = await protoAgent('mining-integrator', setupPrompt(), {
    label: 'staging-setup',
    phase: 'Integrate',
    schema: SETUP_SCHEMA,
  })
  if (!setup || setup.status !== 'ready') {
    throw new Error(`staging setup failed: ${setup?.error ?? 'no result'}`)
  }
  stagingBranch = STAGING_BRANCH
  for (const i of landable) {
    const r = await protoAgent('mining-integrator', landPrompt(i.brief, i.result), {
      label: `land:${i.brief.slug}`,
      phase: 'Integrate',
      // Landing is the serial tail of the batch and is mechanical: cherry-pick,
      // run the gate commands, compare diff verdicts, squash. The judgement was
      // already spent by the reviewer. Deferral is always the safe branch.
      effort: 'low',
      schema: LAND_SCHEMA,
    })
    if (r && r.status === 'landed') {
      landed.push({ slug: i.brief.slug, increment: r.increment, class_name: i.brief.class_name, commit: r.commit, summary: r.summary })
      log(`landed: Mining increment ${r.increment}: ${i.brief.class_name}`)
    } else {
      deferred.push({ slug: i.brief.slug, phase: r?.phase ?? 'integrate-unknown', reason: r?.notes || r?.summary || 'integrator returned no result' })
      log(`${i.brief.slug}: deferred at integration (${r?.phase ?? 'unknown'})`)
    }
  }
}

// ---------- Report (the main agent adds cleanup + manual TEST-look steps) ----------
return {
  smoke: SMOKE,
  staging_branch: stagingBranch,
  staging_worktree: stagingBranch ? STAGING_WT : null,
  candidate_worktrees: candidates.map((c) => `${WT_ROOT}/${c.slug}`),
  candidate_branches: candidates.map((c) => `mining/cand-${c.slug}`),
  landed,
  deferred,
  failed,
  next_steps: stagingBranch
    ? `Staging branch ${stagingBranch} is linear, one commit per increment. Manually spend ONE TEST look per increment in order (fast-forward to each commit, then: uv run rulekit --project projects/gsm8k bench --slice test --spend-test-look). Precision holds → keep; drops → revert that commit. Fast-forward main only past survivors. The pipeline never touches TEST or main.`
    : 'Nothing landed; no TEST looks to spend.',
}
