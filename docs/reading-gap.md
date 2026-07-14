# The reading gap — ANSWERED (2026-07-14). It is a LONG TAIL.

> ## ⛔ THIS BRIEF IS CLOSED. DO NOT RE-RUN IT.
>
> It ran exactly as written. The measurement came back **long tail**, hitting stop condition 1
> (§7 below). **GSM8K coverage is DONE** at 103/0 dev-train, 40/0 dev-holdout, 91.7% TEST —
> converged, not failed. Nothing was built; nothing was broken.
>
> **Two findings, both in `docs/negative-results.md` ("The reading gap is a LONG TAIL"):**
>
> 1. **67% of the "reading gap" is not a reading gap.** 670 of the 1,002 items decline because
>    *the ask shape never fired* (`no ask shape recognizes this question`, `no 'X' events
>    known`). Reading their premises converts **zero** of them — they sit behind the
>    ask-shape wall, the seam already closed. The premise-blocked sub-pool is 332, and 332 is
>    a **ceiling, not a yield**.
>
> 2. **The structural clusters do not predict their own mechanism.** Under a null control
>    (does the cluster's decline reason concentrate above a random subset of the same size?),
>    the three largest clusters score **+0%, +1%, +1%**. `affine-comparative` — the
>    Randy-the-mango-trees family this brief called "the reason to be hopeful" — scores
>    **−3% on 14 items**. *The hypothesis was falsified by its own headline example.*
>
> And the trap that §5 warned about caught one more: `coordinated-qty`, the strongest-looking
> cluster (+16%), turned out to be **11/30 fold-CONFLICT declines** — the engine reading the
> sentence correctly and a *precision guard* firing. It would have been the obvious first
> mining brief, and "fixing" it would have broken a guard.
>
> **The next lever is a different corpus, not a deeper one → `docs/difg-corpus-plan.md`.**
>
> The rest of this file is preserved as the brief that was executed — the method in §4 and the
> traps in §5–6 are sound and are why the answer is trustworthy.

---

**Self-contained brief. Read `CLAUDE.md` (the constitution) and this file. You do not need
to read the rest of `HANDOFF.md` to start.**

Status: **nothing built, nothing broken.** Tree clean at `f524344`, pushed. This is a
measurement task with a hard stop condition, not a build.

---

## 1. Where the project actually is

```
dev-train    103 correct / 0 wrong   (3,772 items)   100% precision
dev-holdout   40 correct / 0 wrong   (3,701 items)   100% precision
suite         52/52 · pytest 998 · lint 0 errors
TEST          11/1 (91.7%) across 124 looks          <- 1 persistent wrong since look #1

coverage 2.7%  =  fully-read 39.0%  ×  hit-rate 7.0%
```

Precision has never dropped on DEV. Every increment that dropped TEST precision was
reverted. That discipline is not negotiable and is the reason the numbers are trustworthy.

## 2. What is exhausted, and what is left

**Exhausted — do not restart these.** All measured, all recorded in `docs/negative-results.md`:

| | verdict |
|---|---|
| Mining ask-shape classes | 5 batches, **+2 net**, two empty. The seam is worked out. |
| The 481-item "per-unit rate" seam | The mechanism **already exists**. 481 was a ceiling, not a yield. |
| Composition (`docs/composition.md`) | **ABANDONED at Phase 0.** Typed ceiling ~13 items. |
| The month/time seam | 220 items, all declining. The guard relaxation measures **0 SOLVED**. |
| The `GroupTotal` consumer fix | Correct, sound, **0 SOLVED**. Written, measured, NOT landed. |

**What is left — and it is the whole ballgame:**

> **81% of the addressable pool is a READING gap. The engine never extracts the numbers.**

```
addressable declining items (fully-read, no unknown words)   1,435
  no numeric facts extracted at all                            292   20%
  gold NOT reachable from the extracted facts                  872   61%
  ─────────────────────────────────────────────────────────────────
  THE READING GAP                                            1,164   81%
```

The canonical example, and the reason to be hopeful:

```
"Randy has 60 mango trees. He also has 5 LESS THAN HALF AS MANY coconut
 trees as mango trees. How many trees does he have?"          gold 85

  numeric facts the engine extracted:  [60.0]
```

That is an **affine relation** — and increment 126 (landed this session) added exactly that
family in the *nominal* frame. **The reading gap may not be a long tail. It may be a handful
of premise surfaces that do not fold.**

This is also the *right kind* of target: it is the **premise half** — the half whose absence
made every ask-shape brief a dead brief (`.claude/workflows/mine.js`, `premise_mechanism`).

---

## 3. THE TASK

For each of the ~1,164 reading-gap items: **find the premise sentence that yields no fact,
and cluster those sentences by STRUCTURE.**

Then answer one question: **is the reading gap a handful of surfaces, or a long tail?**

- **A handful** → mining resumes with a target that actually converts. Each cluster is a
  premise-machinery brief, which is what the shape gate has been asking for all along.
- **A long tail** → GSM8K coverage is done. Say so, record it, and move to the difg
  multi-domain corpus (`docs/difg-corpus-plan.md`).

Either answer is a real result. **Do not let it become a build.**

## 4. Method

Throwaway scratchpad script (methodology §4 — never commit it). Load the slice with:

```python
from rulekit.data.project import load_project
from rulekit.harness.firewall import load_dataset, slice_items
from rulekit.kernel.engine import solve

root = Path('projects/gsm8k'); proj = load_project(root); reg = proj.registry
ds = proj.doc.datasets['gsm8k']          # NOTE: nested under 'gsm8k'
train = load_dataset(root/ds['train'].parquet, ds['train'].question, ds['train'].answer)
test  = load_dataset(root/ds['test'].parquet,  ds['test'].question,  ds['test'].answer)
items = slice_items(train, test, 'dev-train')

r = solve(it.text, reg, tracing=False)   # tracing=False or bench pays 61% deepcopy
```

Per item: keep it if declining AND fully-read (`not any(w for rd in r.premises for w in
rd.unknown_words())`). Then, **per premise reading**, find which ones produced **no fact**
(match `f.provenance.sentence` against `reading.sentence_index`). Those are the unread
sentences. Cluster them.

**Cluster by STRUCTURE, never by lexical frame.** This is the single most important
instruction on this page and it has inverted a conclusion three times:

> By word-frame the addressable pool looked like *616 clusters over 678 items* — hopeless.
> By semantic family the SAME items gave per-unit 100 / total 90 / money-cost 78 / partitive
> 70. **Same data, opposite conclusion.**

Suggested structural axes: the comparative/affine frame (`N more/less than K times …`),
partitive (`half of`, `a third of`), distributive (`each`/`every`/`per`), rate
(`per hour`, `an hour`), possessive-qualified entities, coordinated VPs, relative clauses.

## 5. ⚠ THE TRAP THAT NEARLY COST A DANGEROUS BUILD — READ THIS

**A reachability bound without a null control is not evidence.**

Yesterday I measured "271 items whose gold is reachable from the extracted facts in ≤3
arithmetic ops" and wrote a four-phase roadmap around it. Then:

```
oracle reaches the TRUE gold                439  (38%)
oracle reaches a WRONG, randomly reassigned gold   373  (33%)   <- the null
signal above chance                         +66   (+6%)
```

The search space was big enough to hit almost any target by coincidence. **The 271 was a
fact about the search, not about the corpus.**

**Applied to THIS task:** if you claim "cluster X accounts for N items", you must show that
the cluster predicts *those* items and not an arbitrary N items. Concretely: **sample 10
items from the cluster and hand-verify the missing fold is genuinely the same mechanism.**
A regex that matches 200 sentences is not a class. (`docs/negative-results.md` — "the
worklist counts surfaces, not shapes".)

## 6. The other traps, in one line each

All earned the hard way; all in `docs/negative-results.md`:

- **Prose does not enforce.** Every rule that mattered had to become a gate or a schema
  field. I wrote a retargeted worklist into HANDOFF and the scout — correctly — ignored it.
- **An enabler must be BOUGHT, not promised.** 0 SOLVED means the change *does not fire on
  text we can check*. Two increments died at TEST exactly this way. Infrastructure briefs
  are retired in the gate.
- **`0 BROKE by construction` is not `0 wrongs by construction`.** Argue precision-safety
  against **DECLINE → WRONG**, never against BROKE.
- **A clean DEV gate is necessary and NEVER sufficient.** 7,473 DEV items said increment 81
  was safe. TEST killed it.
- **Spend TEST looks from the MAIN checkout.** Every worktree has its own gitignored
  `snapshots/`; five ledger rows were lost this way. `wc -l test-ledger.jsonl` must equal
  looks spent (currently 120 rows + 1 reconciliation entry = 124 looks).

## 7. Stop conditions (recorded now, while it is cheap to be honest)

- **The top 5 structural clusters cover < ~150 items, or fail hand-verification at 10/10.**
  → long tail. GSM8K coverage is done. Record it and move to the difg corpus.
- **A cluster's "missing fold" turns out to need a word list or a per-problem branch.**
  → constitution rule 1 or 2. The answer is no, regardless of yield.
- **This turns into a build before the clustering is verified.** → stop, you have skipped the
  measurement, and the measurement is the deliverable.

## 8. If it comes back a handful

Re-cut each cluster as a mining brief that names **both halves** (the premise mechanism AND
the ask that folds it) — `evidence.premise_mechanism` is now a required schema field in
`.claude/workflows/mine.js`, and it exists precisely for this. Then `/mine 5` as usual: full
dev gate per increment, constitution review, **one TEST look per landed increment**, a
precision drop reverts that commit.

The gates are all tightened and the pipeline self-test passes end to end. You can trust it.
