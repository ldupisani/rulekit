# Ordered batch outcomes

These invented questions exercise the same structure with different events.
Each first/next batch is disjoint, and its count contributes to the complete
opening population. Each fraction applies only to its own batch.

## Inspection

> Tova starts with 120 boxes. Of the first 80 boxes, she inspected 5/8 of them.
> Out of the next 40 boxes, she inspected one fourth of them.
> How many boxes did Tova not inspect?

Answer: **60** — 50 inspected in the first batch and 10 in the second.

## Reading

> Tova starts with 120 pages. Of the first 80 pages, she read 5/8 of them.
> Out of the next 40 pages, she read one fourth of them.
> How many pages did Tova not read?

Answer: **60**. Asking “How many pages did Tova read?” also answers **60**.

## Three batches

> Mira starts with 150 tennis balls. Of the first 60 balls, Mira hit half of them.
> Of the next 30 balls, Mira hit one third of them.
> Of the next 60 balls, Mira hit one third of them.
> Out of all the tennis balls, how many did Mira not hit?

Answer: **90** — the three batches contribute 30, 10 and 20 hits.
Repeated counts remain distinct batches rather than being deduplicated.

## Supported wording changes

- “Of” and “Out of” introduce the counted batches.
- An event may be stated directly or as “manages/managed to” perform it.
- Word fractions, numeric fractions and percentages use the same calculation.
- An opening may state possession, an initial count, or loading a container.
- Fronted “Out of all …” questions and ordinary “How many … did … not …?”
  ask for the complement. Positive event-total questions reuse the evidence.

The engine declines when batches overlap or fail to exhaust the opening
population, when participants/events/objects disagree, or when the evidence
implies fractional discrete objects. Intentions, attempts and missing temporal
evidence do not become successful events. No answer is inferred for unstated
batches.

## Independent acquisitions and selective disposal

The same `BatchEvidence`, numeric-accounting gate, fraction evaluator and
resource-balance arithmetic also support newly acquired batches. These batches
do not have to partition an opening stock. Standalone acquisitions remain
ordinary `Quantity` facts, so ratios and discourse-group totals keep using
their existing infrastructure. The batch consumer interprets those quantities
locally when a selection or disposal requires batch scope. Each fraction belongs
to its own acquisition, never the accumulated balance.

> Nora downloaded 300 files and deleted 60% of them because they were irrelevant.
> She downloaded 200 more files but realized that three fourths of them were not useful.
> How many valuable files was Nora left with after deleting the unrelated files
> she downloaded in the second round?

Answer: **170 files** — 120 from the first acquisition plus 50 from the second.

Acquisitions can use download, collect or receive; disposals can use delete,
discard or reject. Files, documents, images, photos and other countable objects
reuse the same arithmetic. Supported constructions include:

- “After downloading …, she deleted …” and “She downloaded … and deleted …”.
- A separate acquisition followed immediately by “She deleted half of them” or
  “She realized that half of them were irrelevant”.
- Percentages, numeric fractions and word fractions; optional “more” and “again”.
- Helpful/useful/relevant/valuable and irrelevant/unrelated/unhelpful/useless,
  including negated classifications such as “not helpful”. These are a declared
  binary relevance classification, not a general synonym substitution.
- “How many … remain?”, “… does Nora have left?”, “… was Nora left with?” and
  “… did Nora delete?”. Questions can name the first, second, third or last round.

Classification does not itself delete anything. Before the final deletion in
that example, **320 total files** remain, including **170 useful files** and
**150 irrelevant files**. A qualified disposal question counts only the requested
class; deleting irrelevant files does not count as deleting useful files.

A batch with no stated disposal retains its full count; a quality-specific
question still needs classification evidence for every batch. The consumer
declines for an ambiguous/nonadjacent fraction,
changed participant or item, nonexistent round, mismatched acquisition/disposal,
additional unread event, fractions outside one whole, or fractional object counts.
It does not infer that a fraction of all accumulated files refers to the latest
batch. Earlier nonnumeric narrative is outside the batch interval; a pronoun
there can still carry a reader diagnostic without affecting the supported
numeric evidence.
