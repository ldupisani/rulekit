"""Designer-only rule generation and human review tooling.

The runtime kernel never imports this package. Generation deliberately calls
the ordinary analyzer and matcher as its validation oracle.
"""

from .candidate import GenerationCandidate, RuleAvailability
from .reviews import (
    ReviewRecord,
    append_review,
    delete_review,
    read_reviews,
    update_review,
)
from .sample import GenerationError, generate_candidate, list_rule_availability

__all__ = [
    "GenerationCandidate",
    "GenerationError",
    "ReviewRecord",
    "RuleAvailability",
    "append_review",
    "delete_review",
    "generate_candidate",
    "list_rule_availability",
    "read_reviews",
    "update_review",
]
