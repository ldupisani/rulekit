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
      required: ['pool_frequency', 'structural_sample', 'premise_mechanism', 'same_items'],
      properties: {
        // AN ASK SHAPE WITHOUT ITS PREMISE MACHINERY IS A DEAD BRIEF.
        //
        // This is why ask-shape candidates keep dying at the shape gate at 0-2 of 12,
        // batch after batch, even when drawn correctly from the addressable pool. The
        // ask is genuinely missing — and ADDING IT ALONE CONVERTS NOTHING, because the
        // premises never derive the quantity the ask would fold:
        //
        //   "Calculate the total time the eight runners took to finish the race."
        //     facts today: Quantity(world, runner, 8)   Quantity(runner, hour, 2)
        //     gold:        8 x 2 = 16
        //     missing:     nothing reads (runner, hour, 2) as a PER-RUNNER RATE, so
        //                  there is no total for any ask to return.
        //
        // The gate has been telling us this for four batches. A brief must therefore
        // account for BOTH HALVES, and say plainly which of them is missing.
        premise_mechanism: {
          type: 'string',
          description: 'REQUIRED. For a walked item that does NOT resolve today: name the PREMISE-side mechanism that must exist for the ask to have anything to fold — the fact(s) the premises must yield, and whether they already do. If the premises already produce them and only the ask is missing, say so explicitly ("premises already yield Quantity(x, y, N); the ask shape is the only gap") — that is the ONE case where an ask-only brief is legitimate. If they do not, this brief must build BOTH, or it is a dead brief and you should not propose it.',
        },
        // ────────────────────────────────────────────────────────────────────
        // THE MUTUAL BLOCK (docs/negative-results.md; docs/dual-brief.md §1).
        //
        // MEASURED, from both directions:
        //   Fix the READING -> the items die at the ASK wall  (67% of the reading gap).
        //   Fix the ASK     -> the items die at the READING gap (a working compositional
        //                      parser reads 24 questions correctly; all 24 die on facts).
        //   => THE TWO GAPS ARE MUTUALLY BLOCKING. Neither side alone converts anything.
        //
        // This is why EVERY single-sided increment measured 0 SOLVED: the 481 per-unit
        // seam, GroupTotal, month/time, save->acquire, the future_modal widening, and the
        // compositional ask frame. Not bad luck; not exhausted seams. A declining item is
        // blocked on SEVERAL COORDINATES AT ONCE, and fixing one leaves it on the next.
        //
        // `premise_mechanism` above says which halves are missing. It is NOT enough: a
        // brief can name both halves plausibly and still convert nothing, because the two
        // halves are missing on DIFFERENT items. The only proof a brief is real is the set
        // of items where its halves are JOINTLY SUFFICIENT — where these fixes, together,
        // are the LAST blockers.
        //
        // PROSE DOES NOT ENFORCE. This is a schema field, not a note in HANDOFF, because
        // the last retargeting written into prose was correctly ignored by the scout.
        same_items: {
          type: 'array',
          minItems: 3,
          items: { type: 'string' },
          description: 'REQUIRED. Item IDs (dev-train) where BOTH halves of this brief are the LAST remaining blockers — i.e. items this increment actually CONVERTS declined->correct. You must have WALKED these items and verified that nothing else blocks them: read the premises, check the facts the engine already has, check the ask parses (or that this brief supplies it). A frequency count is a CEILING, not a yield (the 481 lesson) — this list is the yield. If you cannot name 3 such items, the two halves are missing on DIFFERENT items and this brief converts nothing: DO NOT PROPOSE IT.',
        },
        // THE YIELD ESTIMATE (methodology §9). Matches for this class's ASK FAMILY
        // within the ADDRESSABLE POOL — items that are fully-read (no unknown words)
        // AND declining. That is the candidate's ceiling. Cluster the pool by
        // SEMANTIC family, never by lexical frame: by word-frame the pool looks like
        // 616 clusters of ~1 item; by family it is per-unit 100 / total 90 /
        // money-cost 78 / partitive 70. Same items, opposite conclusion.
        pool_frequency: { type: 'number', description: 'items in the ADDRESSABLE POOL matching this ask family — the yield ceiling. Below 3 the candidate cannot yield 3 and is dropped.' },
        // The old surface count across ALL 3772 items. Banned as evidence: it has
        // twice pointed at classes that resolved nothing (327, 444). Report it only
        // as context, never as justification.
        frequency: { type: 'number', description: 'SURFACE count across all items. NOT evidence — context only. See docs/negative-results.md.' },
        stats_reason: { type: 'string' },
        worklist_ref: { type: 'string' },
        // A frequency count is a SURFACE count: it says how many items contain a
        // phrase, not how many have premises the mechanism can consume. Batch 22
        // burned three implementer runs on that confusion (see
        // docs/negative-results.md, "the worklist counts surfaces, not shapes").
        // So a frequency claim must be backed by items actually walked.
        structural_sample: {
          type: 'array',
          minItems: 8,
          description: 'Items from the pool, WALKED — AT LEAST 8. The gate needs >= 3 of them resolving, i.e. a ~38% resolve rate, NOT perfection. Walking only 3 made the gate demand 3-of-3 (100%) and killed excellent candidates: batch 37 lost two classes at 2-of-3, one of them a 354-item family. Walk 8-12; a class that resolves 3 of 10 against a 70-item family is worth ~20 answers.',
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
      description: 'RETIRED — always leave false. A standalone 0-SOLVED enabler can no longer land: increments 128-retry and 129 both cleared the old infra bar with an honest prediction, passed a spotless DEV gate, and each manufactured a CONFIDENT-WRONG on TEST (see docs/negative-results.md, "the infrastructure trap"). An enabler must be BOUGHT, not promised: fold it into the increment that cashes it in, so its yield and its risk are measured in the SAME gate. If nothing can cash it in yet, it is not ready.',
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
    pool_frequency: 0,
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
  // Each of those three now carves SMOKE out EXPLICITLY (`!SMOKE`), because the
  // `infrastructure` flag they used to ride on is retired (the infra trap — see the
  // shape gate). The flag below is kept only so the brief still validates against the
  // schema; it no longer grants anything.
  //
  // WHEN YOU ADD OR CHANGE A GATE, ENUMERATE ITS READERS AND CARVE SMOKE OUT OF IT.
  // This brief is a no-op BY CONSTRUCTION and can never solve anything, so every
  // coverage gate will kill it by default. That has already broken the self-test twice
  // — once silently, with /mine --smoke still reporting green while no longer
  // exercising the Integrate stage at all.
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

// DEAD-CLASS GATE. A class that has failed repeatedly, through DIFFERENT gates, is not
// a candidate — it is a known-blocked class, and every re-proposal costs an implementer
// run. Prose stop-rules in HANDOFF do not hold: `equal-share-division` was recorded as
// blocked and the scout proposed it again the very next batch. A rule that keeps being
// broken needs a mechanism, not a comment.
//
// A class leaves this list when its NAMED blockers land — not because a scout feels
// differently about it.
const DEAD_CLASSES = {
  'equal-share-division': `blocked, 4 failures through 4 different gates (goal-mode 0 SOLVED x2, a rule-1 review kill, and 1-of-12 on an honest walk). Its blockers are NAMED and none have landed: (a) "each one" — the word 'one' senses only as a value, never a noun, so it cannot fill a recipient-noun slot; (b) elided-measure events ("Priya collected 29") fold as a Predication with a string dobj, never a Quantity, so the dividend has no holder; (c) a trailing "...if they divide X amongst themselves?" fuses the division premise INTO the question sentence, and read-phase pattern rules only run over premise readings. Land those first.`,

  // difg. NOT blocked-by-machinery — blocked by CONSTITUTION §2. `probability` is a
  // difg ORCHESTRATOR ID, not a mechanism: its 6 DEV items want ~8 unrelated formulas
  // wearing one domain label. Shipping "the probability domain" ships 8 one-off branches
  // — `vocab_singles` with a domain label stapled on, which the reviewer kills on rule 2.
  // It leaves this list only if a walk proves >= 3 items under ONE mechanism (in which
  // case brief THAT sub-class under its own slug, not the domain).
  'probability': `DEAD on constitution §2 (heterogeneous domain, not a class). difg's domain labels are orchestrator ids, not mechanisms; probability's items need ~8 unrelated formulas, so the honest mechanism is 8 one-off branches. Named a §2 trap in docs/HANDOFF.md and deferred at the arithmetic landing. If a walk finds >= 3 items sharing ONE formula/opcode, brief that SUB-CLASS under its own slug — the domain itself stays dead.`,
}
const deadClass = (slug) => Object.keys(DEAD_CLASSES).find((k) => slug.includes(k))

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
  // THE SMOKE CARVE-OUT — ONE PLACE, ABOVE EVERY GATE, ON PURPOSE.
  //
  // The self-test's brief is a no-op BY CONSTRUCTION: it solves nothing, matches
  // nothing, and has a pool_frequency of 0. EVERY coverage gate will therefore kill it
  // by default, and each new gate kills it again.
  //
  // It used to survive by riding the `infrastructure` flag, whose early-return happened
  // to short-circuit past the yield gate as a SIDE EFFECT. Retiring that flag exposed
  // smoke to a gate that never read it, and the self-test died — the SECOND time a gate
  // change has silently broken /mine --smoke (see SMOKE_BRIEF). Enumerating the readers
  // of a FLAG is not enough when the flag is also acting as a control-flow BYPASS.
  //
  // So: one carve-out, here, before anything else. Any gate added below inherits it for
  // free, and no future gate can break the self-test by forgetting about it.
  if (SMOKE) return true

  const dead = deadClass(c.slug)
  if (dead) {
    unproven.push({ slug: c.slug, phase: 'scout-dead-class', reason: `DEAD CLASS: ${DEAD_CLASSES[dead]}` })
    log(`${c.slug}: DROPPED at the dead-class gate — ${dead} is known-blocked. Not spending an implementer on it again.`)
    return false
  }
  const walked = c.evidence?.structural_sample ?? []
  // THE INFRASTRUCTURE TRAP (docs/negative-results.md). The old bar let a 0-SOLVED
  // enabler land if it NAMED what it would unblock and showed >= 3 items that WOULD
  // resolve once that class arrived. It asked for a PREDICTION — and got an honest,
  // well-argued one every time. Increments 128-retry and 129 both cleared it, both
  // passed a spotless DEV gate (0 BROKE, 0 DECL->WRONG on 3,772 items), and both
  // manufactured a confident-wrong on TEST. 129 gained a correct answer AND a wrong
  // one: coverage up, precision DOWN.
  //
  // 0 SOLVED is not a neutral fact. A widening that converts nothing on DEV has proved
  // exactly one thing — its new bindings DO NOT FIRE ON TEXT WE CAN CHECK. TEST is
  // where they fire, and there is no gold there to catch them. The DEV gate's silence
  // was the absence of evidence, not evidence of absence.
  //
  // So the hatch is closed. An enabler is BOUGHT, not promised: it lands folded into
  // the increment that cashes it in, where its yield and its risk are measured in the
  // SAME gate. If nothing can cash it in, it is not ready.
  if (c.infrastructure) {
    unproven.push({
      slug: c.slug,
      phase: 'scout-infra-retired',
      reason: 'INFRASTRUCTURE BRIEFS ARE RETIRED. A standalone 0-SOLVED enabler cannot land: increments 128-retry and 129 both cleared the old bar with an honest prediction, passed a spotless DEV gate, and each shipped a confident-wrong to TEST (docs/negative-results.md, "the infrastructure trap"). Re-cut this as ONE increment that includes the class it unblocks, so the enabler is bought rather than promised — or drop it until something can cash it in.',
    })
    log(`${c.slug}: DROPPED — infrastructure briefs are retired (the enabler must be bought, not promised; see negative-results.md).`)
    return false
  }
  // YIELD GATE (methodology §9): pool_frequency is the candidate's ceiling — matches
  // within the addressable pool (fully-read AND declining). A class with fewer than 3
  // addressable items CANNOT yield 3, so no implementer is spent on it, however
  // impressive its surface frequency. (Surface frequency has twice pointed at classes
  // that resolved nothing: 327 and 444.)
  const pool = c.evidence?.pool_frequency
  if (!(pool >= 3)) {
    unproven.push({
      slug: c.slug,
      phase: 'scout-yield-gate',
      reason: `yield ceiling too low: pool_frequency=${pool ?? 'MISSING'} (need >= 3). This is the count of ADDRESSABLE items (fully-read AND declining) matching the ask family — the most this class could ever win. Surface frequency=${c.evidence?.frequency ?? '?'} is not evidence (methodology §9).`,
    })
    log(`${c.slug}: DROPPED at the yield gate — pool_frequency=${pool ?? 'MISSING'} < 3. Ceiling too low to be worth an implementer.`)
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
  // `infrastructure` no longer rescues a 0-SOLVED candidate (the infra trap — see the
  // shape gate above). SMOKE still does, and only SMOKE: its brief is a no-op by
  // construction and CANNOT solve anything, so demoting it would kill the self-test.
  return Number.isFinite(solved) && solved === 0 && !SMOKE
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
// THE INFRA SLOT IS GONE. It let exactly one 0-SOLVED enabler land per batch, and both
// times it was used the increment shipped a confident-wrong to TEST after a spotless DEV
// gate (128-retry, 129 — docs/negative-results.md). An enabler is BOUGHT, not promised.
// SMOKE remains exempt, and is the ONLY exemption.
const enforced = reviewed.filter(Boolean).map((i) => {
  if (!i.result || i.result.status !== 'gated') return i
  if (SMOKE) return i
  const solved = solvedCount(i.result)
  if (Number.isFinite(solved) && solved > 0) return i
  log(`${i.brief.slug}: GATED but 0 dev-train SOLVED — demoted to failed (the enabler must be bought, not promised)`)
  return { ...i, result: { ...i.result, status: 'failed', notes: `goal-mode demotion: dev-train SOLVED=0. Infrastructure briefs are retired — an enabler lands folded into the increment that cashes it in, so its yield and its risk are measured in the same gate (docs/negative-results.md, "the infrastructure trap"). ${i.result.notes ?? ''}` } }
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
  // Land biggest-ceiling first (methodology §9): if a later pick conflicts or fails its
  // re-gate, the coverage already banked is the most that was available.
  .sort((a, b) =>
    (b.brief.evidence?.pool_frequency ?? 0) - (a.brief.evidence?.pool_frequency ?? 0) ||
    a.brief.priority - b.brief.priority)

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
