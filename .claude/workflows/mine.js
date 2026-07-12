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
// The branch every candidate is cut from and every gate is measured against.
// Defaults to main. Set it to a parked enabler branch to build a PAYOFF batch on
// top of machinery that has not landed yet: the staging branch then carries
// enabler + payoff, and ONE TEST look validates both (an enabler landed alone
// costs a look it can only lose precision on — see HANDOFF, increment 66).
// Baselines are taken on BASE, so a junior's SOLVED count measures the payoff's
// own delta, not the enabler's.
const BASE = A.base ?? 'main'
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
      required: ['frequency', 'structural_sample'],
      properties: {
        frequency: { type: 'number' },
        stats_reason: { type: 'string' },
        worklist_ref: { type: 'string' },
        // A frequency count is a SURFACE count: it says how many items contain a
        // phrase, not how many have premises the mechanism can consume. Batch 22
        // burned three implementer runs on that confusion (see
        // docs/negative-results.md, "the worklist counts surfaces, not shapes").
        // So a frequency claim must be backed by items actually walked.
        structural_sample: {
          type: 'array',
          minItems: 3,
          description: 'Items from the counted set, WALKED. At least 3 must have resolves=true or the class is unproven and the candidate is dropped before an implementer is spent (infrastructure briefs exempt).',
          items: {
            type: 'object',
            required: ['item_id', 'premise_shape', 'ask_shape', 'fact_emitted', 'resolves'],
            properties: {
              item_id: { type: 'string', description: 'dev-train item id, so the claim is auditable' },
              premise_shape: { type: 'string', description: 'the premise the mechanism consumes — PARAPHRASED, never verbatim item text (briefs get written back to HANDOFF)' },
              ask_shape: { type: 'string', description: 'the ask, paraphrased' },
              fact_emitted: { type: 'string', description: 'what the mechanism emits, and what consumes it to an answer' },
              resolves: { type: 'boolean', description: 'does this item resolve END TO END under the proposed mechanism? Not "does the ask match" — the ask is the easy half.' },
              resolves_after_unblocks: { type: 'boolean', description: 'INFRASTRUCTURE BRIEFS ONLY: this item does not resolve today, but WOULD resolve once the named `unblocks` class lands on top of this enabler. This is what an infra brief must prove instead of coverage.' },
            },
          },
        },
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
      description: 'true ONLY for an enabler that cannot itself move the number. Exempts the shape gate and the SOLVED>=1 goal-mode gate — so it is the ONE way to land an increment that solves nothing, and it is NOT a free pass: it requires `unblocks` plus >= 3 structural_sample items with resolves_after_unblocks=true. At most one per batch.',
    },
    unblocks: {
      type: 'string',
      description: 'REQUIRED when infrastructure=true: the follow-up CLASS this enabler makes reachable, named as a class (constitution rule 2). "It is generally useful" is not an answer — name what lands next on top of it.',
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

// The composition gate: the staging tip re-proved against MAIN, not against BASE.
const COMPOSE_SCHEMA = {
  type: 'object',
  required: ['verdict', 'evidence'],
  properties: {
    verdict: { enum: ['pass', 'fail'], description: 'pass ONLY if both diffs vs main show 0 BROKE and 0 DECL->WRONG, suite 52/52, pytest green, lint 0 errors' },
    solved_vs_main: { type: 'number', description: "the batch's TRUE dev-train coverage delta, enabler included — the number the TEST look is spent against" },
    evidence: { type: 'string', description: 'the raw diff verdicts vs main for both slices, plus suite/pytest/lint' },
    notes: { type: 'string' },
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
  evidence: {
    frequency: 0,
    stats_reason: 'n/a — pipeline self-test',
    worklist_ref: 'n/a',
    // The smoke brief must be a VALID infrastructure brief, not a special case:
    // it clears the same bar every enabler clears. Keeping it legal by the real
    // rules is what stops the self-test from silently rotting out of the gates
    // (it has now had to satisfy four of them).
    structural_sample: [1, 2, 3].map((n) => ({
      item_id: `smoke-${n}`,
      premise_shape: 'n/a — pipeline self-test, no real item is claimed',
      ask_shape: 'n/a',
      fact_emitted: 'none: the change is a YAML comment and compiles to nothing',
      resolves: false,
      resolves_after_unblocks: true,
    })),
  },
  unblocks: 'n/a — this brief proves the PIPELINE (implement -> review -> integrate), not a problem class',
  mechanism:
    'Add a single YAML comment line at the top of packs/arithmetic/rules/core.yaml (a no-op: comments do not compile into the registry). Write tests/test_mining_smoke-noop.py asserting the full registry still compiles (reuse the full_registry fixture pattern). Expected diff verdict: NEUTRAL on both slices.',
  yaml_only: true,
  files_expected: ['packs/arithmetic/rules/core.yaml', 'tests/test_mining_smoke-noop.py'],
  risks: { blast_radius: 'none — comment-only change', shared_paths: [], quarantine_words: [] },
  priority: 1,
  overlaps_with: [],
  // A no-op brief proves no class and solves nothing BY CONSTRUCTION, so every
  // coverage gate would kill it — the shape gate (no resolving samples), the
  // pre-review `doomed` filter and the post-pipeline goal-mode loop (SOLVED=0).
  // All three already exempt `infrastructure`, so declaring it here makes the
  // smoke candidate legal by the EXISTING rule instead of needing an `if (SMOKE)`
  // in each gate — and any gate added later inherits the carve-out for free.
  // (Before this, the goal-mode gate silently demoted the smoke candidate and
  // /mine --smoke stopped exercising the Integrate stage while still reporting
  // green. Three separate carve-outs is how that happens twice.)
  infrastructure: true,
  evidence_note: 'no-op self-test: proves the pipeline, not a class',
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
BASE=${BASE}

Cut your worktree from BASE (not necessarily main) and take your baselines on it.
Your SOLVED count is therefore YOUR delta on top of BASE, which is what the gate
measures.

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
BASE=${BASE}
Diff to review: git diff ${BASE}...${r.branch}

Review THIS candidate's own diff — the range is against BASE, not main. If BASE
is not main, the branch sits on top of an enabler whose commits were already
gated and reviewed in an earlier batch; diffing against main would attribute the
enabler's changes to this brief.

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
BASE=${BASE}
DATE=${DATE}

Create the staging branch from BASE (not necessarily main) and take the staging
baselines on it.

Return the setup structured output.`

const composePrompt = () => `COMPOSE MODE. Every gate in this batch was measured against BASE, and BASE is
NOT main — so nothing has yet proven the staging tip against main. Dev gates do
not compose: the enabler on BASE and the increments landed on top of it were each
clean against their own baseline, and can still interact.

Re-prove the FULL dev gate for the staging tip against MAIN's baselines:
build fresh main baselines (bench dev-train and dev-holdout at main, --jobs 8),
then bench the staging tip and diff against those. 0 BROKE and 0 DECL->WRONG on
BOTH slices, suite 52/52, pytest green, lint 0 errors.

Report SOLVED vs main too — that is the batch's TRUE coverage delta, enabler
included, and it is the number the TEST look will be spent against.

MAIN=${REPO}
STAGING=${STAGING_WT}
STAGING_BRANCH=${STAGING_BRANCH}
BASE=${BASE}

Change NOTHING. This is a measurement, not a landing. If the gate fails, say so —
a failure means the composed state is not landable and the batch must be reworked,
NOT that you should fix anything.

Return the ComposeVerdict structured output.`

const landPrompt = (c, r) => `LAND MODE. Land ONE review-passed candidate onto the staging branch per your
agent protocol: cherry-pick, FULL re-gate on the integrated state vs current
staging baselines, finalize (assign increment N, rename test, HANDOFF record),
squash to one commit, advance baselines. Defer (reset --hard to pre-pick) on
any conflict or gate failure — never hand-fix.

MAIN=${REPO}
STAGING=${STAGING_WT}
STAGING_BRANCH=${STAGING_BRANCH}
CANDIDATE_BRANCH=${r.branch}
BASE=${BASE}

The candidate was cut from BASE, so the cherry-pick range is
$(git merge-base ${BASE} ${r.branch})..${r.branch} — NOT merge-base with main.

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

MAIN=${REPO}
BASE=${BASE}
WT_ROOT=${WT_ROOT}
${BASE === 'main'
  ? 'BASE is main: probe in the main checkout as usual.'
  : `BASE IS NOT MAIN — this is a PAYOFF batch built on a parked enabler.
The main checkout does NOT contain that enabler, so probing there would ask a
kernel that lacks the very machinery this batch is built on, and every item the
enabler unblocks would score resolves:false. YOU MUST PROBE ON BASE:

  git -C "$MAIN" worktree add "${WT_ROOT}/scout-probe" ${BASE}
  ln -s "$MAIN/projects/gsm8k/data" "${WT_ROOT}/scout-probe/projects/gsm8k/data"
  mkdir -p "${WT_ROOT}/scout-probe/projects/gsm8k/snapshots"
  cd "${WT_ROOT}/scout-probe" && uv sync --extra bench

Run EVERY stats run, solve probe and structural-sample walk in that worktree, so
\`resolves\` reflects the state candidates will actually be built on. Remove it
when you finish: git -C "$MAIN" worktree remove --force "${WT_ROOT}/scout-probe".
This is the ONE worktree you may create; it is read-only probing, never edits.`}

Return the ScoutOutput structured output.`,
    { label: 'scout', phase: 'Scout', schema: SCOUT_SCHEMA },
  )
  if (!scout || !scout.candidates?.length) {
    return { staging_branch: null, landed: [], deferred: [], failed: [], notes: 'Scout returned no viable candidates — nothing to do.' }
  }
  candidates = scout.candidates.slice(0, COUNT)
  log(`scout selected ${candidates.length} candidates: ${candidates.map((c) => c.slug).join(', ')}`)
  if (scout.notes) log(`scout notes: ${scout.notes}`)
}

// SHAPE GATE (docs/negative-results.md, batch 22): a frequency count says how
// many items contain a phrase, not how many the mechanism can READ. Batch 22
// spent three implementer runs on candidates whose counted items, once walked,
// turned out not to present the targeted shape at all. So a candidate must show
// >= 3 walked items that resolve END TO END, or it never reaches an implementer.
//
// INFRASTRUCTURE is NOT an exemption — it is a DIFFERENT bar. An enabler cannot
// move the number by definition, so it proves its worth by naming the class it
// unblocks (`unblocks`) and showing >= 3 walked items that WOULD resolve once
// that class lands on top of it (`resolves_after_unblocks`). Batch 23 landed a
// 0-SOLVED enabler by simply ticking `infrastructure: true` — honestly, and with
// disclosure, but a self-declared flag that skips both coverage gates is a free
// pass, and the goal-mode gate exists precisely because prose directives were
// being routed around. So the escape hatch stays; the free pass does not.
const unproven = []
candidates = candidates.filter((c) => {
  const walked = c.evidence?.structural_sample ?? []
  if (c.infrastructure) {
    const wouldResolve = walked.filter((s) => s.resolves_after_unblocks).length
    if (c.unblocks && wouldResolve >= 3) return true
    unproven.push({
      slug: c.slug,
      phase: 'scout-shape-gate',
      reason: `infrastructure brief unproven: ${!c.unblocks ? 'no `unblocks` class named' : `names "${c.unblocks}" but only ${wouldResolve} of ${walked.length} walked items would resolve once it lands (need >= 3)`}. An enabler that cannot move the number must show what it unblocks — infrastructure is a different bar, not an exemption.`,
    })
    log(`${c.slug}: DROPPED at the shape gate — infrastructure brief without a proven payoff (${!c.unblocks ? 'no unblocks class' : `${wouldResolve}/${walked.length} would-resolve`}).`)
    return false
  }
  const resolving = walked.filter((s) => s.resolves).length
  if (resolving >= 3) return true
  unproven.push({
    slug: c.slug,
    phase: 'scout-shape-gate',
    reason: `class unproven: ${resolving} of ${walked.length} walked items resolve end-to-end (need >= 3). frequency=${c.evidence?.frequency ?? '?'} is a SURFACE count — it does not show the mechanism can read those items. See docs/negative-results.md, "the worklist counts surfaces, not shapes".`,
  })
  log(`${c.slug}: DROPPED at the shape gate — ${resolving}/${walked.length} walked items resolve (need 3). Not spending an implementer on an unproven class.`)
  return false
})
if (!candidates.length) {
  return { staging_branch: null, landed: [], deferred: unproven, failed: [], notes: 'Every candidate failed the shape gate: frequency claims with no walked items that resolve end-to-end. Nothing implemented.' }
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
//   - SMOKE: the self-test's brief is a no-op by construction and can never
//     solve anything. This is the THIRD gate that has to know that (with the
//     shape gate and the post-pipeline loop) — the 2026-07-12 smoke run died
//     here after the other two were carved out.
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
const deferred = [
  // candidates dropped at the shape gate, before any implementer was spent
  ...unproven,
  ...items
    .filter((i) => i.result.status === 'deferred')
    .map((i) => ({ slug: i.brief.slug, phase: 'implement-deferral', reason: i.result.notes || i.result.summary })),
]
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

// ---------- Phase 5: COMPOSITION GATE (only when BASE !== main) ----------
// Every gate in this batch was measured against BASE. If BASE is a parked enabler,
// then the enabler was gated against main in ITS batch, and the payoff was gated
// against the enabler here — but NOTHING has gated enabler+payoff against main.
// "Parallel dev gates don't compose" is this campaign's founding lesson and it
// applies across batches too: two changes each clean against their own base can
// still interact. So the staging tip must re-prove the FULL gate against main
// before any of it is a landing candidate.
let composition = null
if (stagingBranch && BASE !== 'main' && landed.length) {
  phase('Compose')
  composition = await protoAgent('mining-integrator', composePrompt(), {
    label: 'compose-vs-main',
    phase: 'Compose',
    schema: COMPOSE_SCHEMA,
  })
  if (!composition || composition.verdict !== 'pass') {
    log(`COMPOSITION GATE FAILED vs main — the staging tip is NOT landable: ${composition?.notes ?? 'no result'}`)
  } else {
    log(`composition gate PASSED: staging tip is clean vs main (${composition.evidence ?? ''})`)
  }
}

// ---------- Report (the main agent adds cleanup + manual TEST-look steps) ----------
return {
  smoke: SMOKE,
  base: BASE,
  staging_branch: stagingBranch,
  staging_worktree: stagingBranch ? STAGING_WT : null,
  candidate_worktrees: candidates.map((c) => `${WT_ROOT}/${c.slug}`),
  candidate_branches: candidates.map((c) => `mining/cand-${c.slug}`),
  landed,
  deferred,
  failed,
  composition,
  next_steps: stagingBranch
    ? `Staging branch ${stagingBranch} is linear, one commit per increment. Manually spend ONE TEST look per increment in order (fast-forward to each commit, then: uv run rulekit --project projects/gsm8k bench --slice test --spend-test-look). Precision holds → keep; drops → revert that commit. Fast-forward main only past survivors. The pipeline never touches TEST or main.`
    : 'Nothing landed; no TEST looks to spend.',
}
