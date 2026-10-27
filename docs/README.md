# RuleKit references

RuleKit is a deterministic reading and reasoning engine. YAML packs supply
language and domain knowledge; the kernel reads explicit structure, derives
typed facts, and answers only when its evidence supports a commitment.

These documents describe implemented behavior, its limits, and the principles
used to evaluate changes. Feature references link to implementation and tests.
Development history and abandoned plans are available through Git history.

## Foundations

| Reference | Use it for |
| --- | --- |
| [Architecture](architecture.md) | Runtime stages, ownership boundaries, representations, and extension points |
| [Design constraints and failure modes](negative-results.md) | Why identity, scope, accounting, conservative resolution, and independent evaluation matter |
| [Testing methodology](methodology.md) | Synthetic evidence, regression gates, corpus selection, and the DEV/TEST firewall |
| [Corpus reference](corpora.md) | Corpus purpose, typed gold, split policies, and the distinction between coverage and independent evidence |

The canonical project instructions and constitution live in
[CLAUDE.md](../CLAUDE.md). Questions for implementation are selected by the user.

## Language and reasoning

| Reference | Implemented capability |
| --- | --- |
| [YAML authoring](yaml-reference.md) | Pack documents, categories, rules, asks, templates, synthesis, and conversions |
| [Reference resolution](deixis.md) | Participant identity, deictic arbitration, item references, time, and location evidence |
| [Clause scope and assumptions](complementizers.md) | Supported clause routing, comparison predicates, and question-local assumptions |
| [Composition](composition.md) | Typed derivations, recurring budgets, measured regions, batches, mixture ledgers, and evidence accounting |
| [Logic and arithmetic](logic-arithmetic.md) | Exact class membership, role derivation, refinements, and class-scoped quantities |
| [Semantic projection](semantic-projection.md) | Semantic graph facts, graph scoring, project boundaries, and supported diagnostics |

## Authoring

[Designer and review workbench](authoring-workbench.md) describes traces, safe
YAML editing, generation, human reviews, coverage, and revision-pinned evidence.
Executable worked examples and decline boundaries live in the test modules
linked from each feature reference.
