"""Difficulty framing and trap detection models."""

from dataclasses import dataclass, field
from enum import Enum


class TrapCategory(str, Enum):
    """Categories of modeling traps."""

    GRAIN = "grain"
    TEMPORAL = "temporal"
    IDENTITY = "identity"
    SEMANTIC = "semantic"
    RELATIONSHIP = "relationship"


@dataclass
class EnabledTrap:
    """A specific modeling trap that is active in a scenario."""

    category: TrapCategory
    name: str
    threat_description: str  # "will try to break you by..."
    config_source: str  # which config option enables this


@dataclass
class DifficultyBriefing:
    """Complete difficulty briefing for a scenario."""

    difficulty_name: str
    difficulty_description: str
    enabled_traps: list[EnabledTrap] = field(default_factory=list)
    adversarial_tagline: str = ""

    @property
    def traps_by_category(self) -> dict[TrapCategory, list[EnabledTrap]]:
        """Group traps by category."""
        result: dict[TrapCategory, list[EnabledTrap]] = {}
        for trap in self.enabled_traps:
            if trap.category not in result:
                result[trap.category] = []
            result[trap.category].append(trap)
        return result

    @property
    def threat_summary(self) -> list[str]:
        """Generate a list of threat descriptions for display."""
        return [trap.threat_description for trap in self.enabled_traps[:5]]


# Difficulty descriptions
DIFFICULTY_DESCRIPTIONS = {
    "easy": "A forgiving shop with predictable behavior. Good for learning the basics.",
    "medium": "A typical retail shop with some complexity. Expect a few traps.",
    "hard": "A challenging shop with many edge cases. Your model will be tested.",
    "adversarial": "A hostile shop designed to break naive models. Every trap is enabled.",
}

# Adversarial taglines by difficulty
ADVERSARIAL_TAGLINES = {
    "easy": "This shop plays fair... mostly.",
    "medium": "This shop has a few tricks up its sleeve.",
    "hard": "This shop wants to see your model sweat.",
    "adversarial": "This shop hates clean data models.",
}
