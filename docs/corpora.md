# Corpus and judging reference

Projects select their packs, data, splits, and judging contracts. A score is
meaningful only with that configuration. Materialized corpus files and
snapshots are gitignored; builders and project declarations define their
provenance. This reference does not authorize a protected evaluation.

## Answer corpora

| Project | Purpose | Definition |
| --- | --- | --- |
| Curated | Fast regression across explicitly supported constructions, including reference and logic/arithmetic cases | [Project](../projects/curated/project.yaml) |
| GSM8K | Grade-school arithmetic development and protected evaluation | [Project](../projects/gsm8k/project.yaml) |
| ASDiv | Independent word problems with different authors and wording | [Builder](../projects/asdiv/build_corpus.py) |
| SVAMP | Arithmetic questions with adversarial variations | [Builder](../projects/svamp/build_corpus.py) |
| MAWPS | Another arithmetic distribution, with template concentration considered when interpreting results | [Builder](../projects/mawps/build_corpus.py) |
| SciBench | Attempted scientific numeric reasoning and out-of-domain safety | [Builder](../projects/scibench/build_corpus.py) |
| DIFG | Multi-domain coverage inventory with inherited examples and gold limitations | [Builder](../projects/difg/build_corpus.py) |
| FOLIO | Logical labels and arithmetic leakage detection under its configured packs | [Builder](../projects/folio/build_corpus.py) |

For regression work, use the complete declared DEV slice and compare stable
item outcomes. GSM8K's `dev-train` and `dev-holdout` are complementary stable-hash
partitions. The holdout is a validation delta, not a source of tuning examples.
Other answer corpora use their builders' frozen partitions.

The judging and split enforcement live in
[the bench](../src/rulekit/harness/bench.py) and
[the firewall](../src/rulekit/harness/firewall.py).

## Typed gold

The harness supports typed expected answers in addition to ordinary numeric
gold. The comparator distinguishes numbers, quantity-with-unit wrappers,
structured numeric results, verdicts, text, and decline expectations according
to the loaded contract. A formatting adapter must not introduce runtime
knowledge or convert a parser failure into a successful reasoning result.

Unsupported predicted answer types remain declined or wrong under that
contract; the presence of a typed gold does not license a new kernel answer.

Implementation: [typed gold parsing](../src/rulekit/harness/firewall.py) and
[typed judging](../src/rulekit/harness/bench.py).
Tests: [typed gold](../tests/test_typed_gold.py).

## DIFG: coverage, not independent precision

The DIFG builder extracts a predecessor's test cases and demonstrations.
Some golds originate from predecessor output, and the example set is selected
for that system's coverage. A high score therefore measures supported domains
and examples; it does not establish independent generalization.

The builder preserves source/domain metadata, deterministic partitioning, and
its supported gold representations. Raw calculator expressions are excluded
from the natural-language inventory. Do not combine DIFG's score with an
independent corpus's precision claim.

## FOLIO

FOLIO's golds are logical labels rather than arithmetic numbers. Its builder
partitions by premise block so multiple conclusions about the same story do
not leak across the firewall. The `Uncertain` label remains text, not a decline
expectation: an engine that did not understand the question has not proved
uncertainty.

The ordinary [FOLIO project](../projects/folio/project.yaml) is arithmetic-only.
It is expected to make no numeric commitments against logical questions.
Opt-in logic work uses a different configuration, described in
[Logic and arithmetic](logic-arithmetic.md). Do not infer that the safety
project measures the coverage of those separate logical readers.

The human annotation is useful audit evidence, but unsupported or malformed
annotations must not silently replace the declared gold label.

## Semantic projection corpora

COGS and PMB score emitted semantic graphs in the harness. Their metrics do
not mean that the arithmetic solver answered the source sentence.

| Project/slice | Role and boundary |
| --- | --- |
| COGS `dev-train`, `dev-holdout` | Complementary partitions of official training data for development and validation |
| COGS `calibration` | Official development data already sampled during dataset selection; never an untouched holdout |
| COGS `test`, `generalization` | Protected aggregate-only partitions with ledgered access |
| PMB `train`, `development` | Release-provided partitions under the builder's frozen licence filter |
| PMB `test` | Protected English standard-test partition under the same filter |

The [COGS builder](../projects/cogs/build_corpus.py) pins source material,
audits duplicates, and records published-example contamination. Public task
examples cannot be presented as unseen protected evidence.

The [PMB builder](../projects/pmb/build_corpus.py) pins PMB 5.1.0 and checks
release/licence hashes. It admits English gold records with the declared
Tatoeba metadata allowlist and bundled notices. The long-text test set is
outside this contract. Raw materialized text and annotations remain gitignored.
See the builder for exact notices, hash pins, and redistribution conditions.

The [projection reference](semantic-projection.md) explains graph outcomes.
[Testing methodology](methodology.md) explains authorization and regression
rules for every protected slice.
