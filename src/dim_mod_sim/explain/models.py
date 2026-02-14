"""Models for the explain/diagnostic module."""

from dataclasses import dataclass, field


@dataclass
class QueryScenario:
    """A query scenario that demonstrates a schema problem."""

    scenario_name: str
    business_question: str
    setup_description: str  # What events/data are involved
    expected_answer: str  # What the correct answer should be
    actual_with_schema: str  # What the schema would produce
    why_wrong: str  # Business explanation of why it's wrong
    root_cause: str  # Technical cause in the schema
    events_involved: list[str] = field(default_factory=list)  # Event IDs/descriptions
    severity: str = "major"  # critical, major, moderate, minor


@dataclass
class ExplainResult:
    """Complete explanation result showing schema problems."""

    schema_issues_found: int
    query_scenarios: list[QueryScenario] = field(default_factory=list)
    summary: str = ""

    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return self.schema_issues_found > 0
