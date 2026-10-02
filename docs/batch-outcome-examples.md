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
