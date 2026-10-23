# Testing and measurement

The implementation workflow and required checks live in [CLAUDE.md](../CLAUDE.md).
This reference explains the evidence those checks provide. Questions are
selected by the user; corpus diagnostics measure a change's effects.

## Outcomes and priorities

| Outcome | Meaning |
| --- | --- |
| Correct | The committed answer matches the corpus's judging contract |
| Wrong | The engine committed an unsupported or incorrect answer |
| Declined | The engine did not commit; this is not a correct answer |
| Errored | Execution failed; this is not evidence of safe reasoning |

Precision is correct divided by committed answers. Coverage measures how much
of the evaluated population receives a commitment. Precision takes precedence
over coverage: an additional correct answer cannot excuse an unsafe inference.
A decline must remain distinguishable from a justified negative or uncertainty
verdict. [Projection](semantic-projection.md) uses its own graph outcomes.

Fully read, vocabulary coverage, grammar matching, and answer correctness are
different measurements. Admitting words can expose a previously hidden wrong
commitment. A diagnostic ceiling is not a forecast of correct answers.

Implementation: [bench and judging](../src/rulekit/harness/bench.py),
[diagnosis](../src/rulekit/cli.py), and
[projection scoring](../src/rulekit/harness/projection.py).

## Synthetic acceptance evidence

For a supplied question, identify the general language or reasoning capability.
Use invented examples to check:

- simplified versions of the same construction;
- alternative vocabulary, word order, and supported paraphrases;
- distinct contexts for behavior intended to be domain-neutral;
- missing, contradictory, ambiguous, or mismatched evidence;
- the facts, references, units, scope, and arithmetic needed for the answer.

Never copy benchmark prose into test fixtures or committed evidence. Test the
supplied question locally, but report the result separately from independent
benchmark generalization. A rule's generality is not established by changing
only a person's name or a number.

Matching a premise is not enough. Check the full path through the ask,
consumer, and commitment guards. A generated match is authoring evidence,
not a gold answer and not a runtime fact.

## Regression comparisons

Where the change's reach warrants corpus comparisons:

1. Capture a baseline from a known code and registry state.
2. Apply the change and run the same complete slice.
3. Compare stable item identities and outcomes, not just aggregate scores.
4. Require **0 BROKE, 0 DECL→WRONG**: no correct answer becomes a decline or
   wrong answer, and no previously declined item becomes wrong.
5. Validate on DEV holdout with **zero new wrongs**. Existing wrongs remain
   defects; their absolute count cannot conceal a new failure.
6. Review newly committed outcomes and expand synthetic boundaries as needed.

A comparison is meaningful only when corpus, slice, judging contract, and
registry provenance are known. A partial run cannot stand in for a complete
slice. Do not present a broad run followed by repairs as an uninterrupted
full-suite pass; report the actual checks performed.

```sh
uv run pytest -q tests/test_composed_question_families.py
uv run rulekit --project projects/curated bench --slice suite
uv run rulekit --project projects/curated lint
uv run pytest -n 4 --dist=worksteal
uv run rulekit --project projects/gsm8k bench --slice dev-train --snapshot before.json
# Run the same command after the change, writing after.json.
uv run rulekit --project projects/gsm8k diff before.json after.json
uv run rulekit --project projects/gsm8k bench --slice dev-holdout
```

Use the snapshot-producing command before editing when a baseline is required.
The example test module is illustrative; select tests affected by the change.
The project instructions determine when broader testing is required.

## DEV/TEST firewall

GSM8K's `dev-train` and `dev-holdout` use complementary stable-hash partitions.
Tune on DEV-train. DEV holdout is a delta gate: do not tune to its individual
items. Official TEST is separately protected. Dataset-specific policies are
listed in the [corpus reference](corpora.md).

Protected TEST/generalization looks require separate explicit authorization.
They are aggregate-only and ledgered. Do not inspect protected rows or failure
items, run partial protected looks, or repeatedly evaluate a checkpoint as if
each evaluation were fresh evidence. The document browser must not expose
corpus files. An authorized TEST precision drop requires reverting the change,
even when DEV improved; the protected evaluation does not become a tuning set.

Implementation: [firewall](../src/rulekit/harness/firewall.py),
[projection firewall](../src/rulekit/cli.py), and
[document-browser tests](../tests/test_server_doc_firewall.py).

## Independent evaluation

A holdout from the same corpus can expose tuning overfit but cannot reveal a
construction absent from that entire corpus. Relevant cross-corpus comparisons
provide evidence from different authors and distributions. ASDiv, SVAMP, MAWPS,
and SciBench are answer-corpus gates; FOLIO also checks that arithmetic does
not commit numbers against logical questions.

Every evaluated corpus uses the same regression safety bar. SciBench supports
attempted numeric solutions; FOLIO's arithmetic-only project is expected to
make no numeric commitments. DIFG is a coverage inventory, not an independent
precision estimate. COGS and PMB have separate graph-scoring contracts.

Null controls matter. An arithmetic search that also reaches shuffled targets,
an always-yes answer on one-sided labels, or an always-decline engine scored
as correctly uncertain does not establish reasoning. Likewise, source examples
and contaminated calibration data cannot become an untouched holdout by being
renamed.

The underlying design lessons are described in
[Design constraints and failure modes](negative-results.md).
