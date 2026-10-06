# Core English pack organization

Core English describes shared language. Its layout follows linguistic identity
and semantic roles, independently of the example that first needed a word.

- `lexicon/core.yaml` is the alphabetized shared dictionary. Each lexical identity
  has one entry, including all its senses, inflections, and lexical-phrase facts.
  Food, locations, ordinals, and verbs do not acquire separate dictionaries when
  a new arithmetic construction uses them.
- `categories/*.yaml` group category definitions by semantic or grammatical
  responsibility. Direct memberships and category-keyed compatibility declarations
  live beside the category they extend. The base categories are in `core.yaml`;
  reference forms, commerce, mixtures, discourse markers, and other coherent
  domains have their own modules.
- `categories/attributes.yaml` holds numeric lexical attributes. A word can serve
  several roles, so its ordinal, sequence, and batch properties are stored together.
- Numbers, obligations, requirements, and the other pack documents retain their
  own schema-defined responsibilities. Arithmetic constructions live in the
  arithmetic pack rather than defining vocabulary ownership.

To add a word, extend the dictionary and its existing semantic memberships.
Create a category module only for a distinct family of related definitions,
not for the collection of words used by a particular question. Extensions in
other packs may add members without duplicating the shared lexical entry.

`tests/test_core_english_layout.py` checks dictionary ordering, category ownership,
and the single numeric-attribute owner. Pack loading also rejects duplicate
lexical identities.
