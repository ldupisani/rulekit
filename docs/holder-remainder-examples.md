# One remaining holder

Curated supports exhaustive populations whose initial group has either equal
per-holder contents or an explicit collective subtotal:

> There are 4 boxes. Each of the first three boxes has 6 apples. There are a
> total of 27 apples. How many apples does the fourth box have?

The answer is **9**: the known prefix contains `3 × 6 = 18`, leaving `27 − 18`.
The same structure works for houses and decorations or jars and marbles.

A collective prefix stays distinct: “The first three boxes have 6 apples in
total” records 6 for the whole prefix, so a total of 27 leaves **21**. It does
not multiply the subtotal by three. “Altogether”, “together”, “all together”,
“combined”, and “have a total of” also express a collective subtotal.

Supported variations include:

- Content-bearing populations such as “There are 4 jars of pickles”, using
  the existing container-partitive existential rule.
- A combined population and distribution sentence, joined by “and”.
- “Each of the first three boxes has…”, “The first three boxes each have…”,
  and “The first three boxes have…each”.
- “There are a total of…”, “…altogether”, and “…in total”.
- “How many apples does the fourth box have?” and “How many apples are in
  the fourth box?”
- “Last”, “final”, and “remaining” instead of an explicit ordinal.
- A shared location on the population and total, and a local location on the
  per-holder contents. Curated locations include street, road, lane, avenue,
  and boulevard, with “on” preserving the same location scope.
- A question-local conditional total (“If there are a total of…, how many…?”).

Named ordinals through sixth are declared in core vocabulary. Terminal queries
such as “the last box” also work for larger populations. Fused ordinal queries
such as “the 4th box” are not added by this change.

The population and known prefix must leave exactly one holder. The engine
checks whole counts, matching holder/content identities, compatible locations,
complete source coverage, and a nonnegative remainder. Two missing holders,
conflicting totals or locations, additional unread events, and a question about
a different ordinal decline. It never assumes that unknown holders have equal
contents.

Implementation reuses `BatchEvidence` for the prefix and combined population,
with separate per-member and collective-subtotal fields,
ordinary `Quantity` for standalone populations, `GroupTotal` for contents,
and shared multiplication, residual arithmetic, numeric accounting, and source
coverage. The answer carries an exhaustive-partition proof. Fraction/ordinal
ambiguity is resolved only before a compatible noun; ordinary “one fourth of…”
fractions and existing “first”/“second” identity modifiers remain unchanged.
Ordinals stay noun qualifiers, so a fourth box and a fifth box keep distinct
identities even when they contain identical amounts. The new question shapes require typed holder-prefix evidence. A shared,
optional consumer-applicability check keeps explicit holdings and sequence
questions on their existing routes when that evidence is absent. Runtime
selection, accounting, review replay, and Designer traces use the same check;
question-only generation can still inspect the structural shape.

Invented regression examples live in `tests/test_holder_remainder.py`.
