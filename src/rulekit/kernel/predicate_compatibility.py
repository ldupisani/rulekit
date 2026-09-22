"""Object-category-gated predicate meanings, never global verb synonyms."""


def predicate_concepts(verb, theme, reg, *, fallback_to_verb=False):
    """Return every licensed meaning; callers decide whether ambiguity is safe.

    Sequence reconciliation historically treats an ungrouped verb as its own
    meaning. Pairwise synonym checks instead require a shared declared group;
    keeping that choice explicit avoids turning concept labels into synonyms.
    """
    concepts = frozenset(
        concept for concept, (gate, forms) in reg.context_synonyms.items()
        if verb in forms and reg.word_in_category(theme, gate)
    )
    return concepts or (frozenset({verb}) if fallback_to_verb else frozenset())


def predicates_compatible(left, right, theme, reg):
    """Exact identity or membership in one common, locally licensed group."""
    return left == right or bool(
        predicate_concepts(left, theme, reg)
        & predicate_concepts(right, theme, reg)
    )
