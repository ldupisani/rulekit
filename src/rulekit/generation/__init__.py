"""Designer-only rule generation and human review tooling.

The runtime kernel never imports this package. Generation deliberately calls
the ordinary analyzer and matcher as its validation oracle.
"""

from .candidate import GenerationCandidate, RuleAvailability
from .exploration import (
    ExplorationEvent,
    ExplorationFiller,
    ExplorationSelection,
    append_exploration,
    choose_exploration_target,
    exploration_path,
    exploration_status,
    read_exploration_events,
)
from .hypotheses import derive_hypotheses
from .reviews import (
    FactEvidence,
    HypothesisRecord,
    PremiseAttachment,
    ReviewRecord,
    ReviewDefect,
    append_review,
    delete_review,
    read_reviews,
    update_review,
)
from .sample import (
    GenerationError,
    generate_candidate,
    generate_minimal_pair,
    list_rule_availability,
    promote_reading_candidate,
    retest_candidate,
)

__all__ = [
    "GenerationCandidate",
    "GenerationError",
    "ExplorationEvent",
    "ExplorationFiller",
    "ExplorationSelection",
    "FactEvidence",
    "HypothesisRecord",
    "PremiseAttachment",
    "ReviewRecord",
    "ReviewDefect",
    "RuleAvailability",
    "append_review",
    "append_exploration",
    "choose_exploration_target",
    "delete_review",
    "derive_hypotheses",
    "generate_candidate",
    "generate_minimal_pair",
    "exploration_path",
    "exploration_status",
    "list_rule_availability",
    "promote_reading_candidate",
    "read_reviews",
    "read_exploration_events",
    "retest_candidate",
    "update_review",
]
