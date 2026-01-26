"""Evaluation result models."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Severity level of a deduction."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class Deduction:
    """A scoring deduction with explanation."""

    points: int
    reason: str
    severity: Severity
    affected_elements: list[str] = field(default_factory=list)


@dataclass
class AxisScore:
    """Score for a single evaluation axis."""

    axis_name: str
    score: int
    max_score: int
    deductions: list[Deduction] = field(default_factory=list)
    commentary: str = ""

    @property
    def percentage(self) -> float:
        """Get score as percentage."""
        return (self.score / self.max_score * 100) if self.max_score > 0 else 0


@dataclass
class EvaluationResult:
    """Complete evaluation result."""

    total_score: int
    max_possible_score: int
    axis_scores: dict[str, AxisScore] = field(default_factory=dict)
    critique: str = ""
    recommendations: list[str] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        """Get total score as percentage."""
        return (self.total_score / self.max_possible_score * 100) if self.max_possible_score > 0 else 0

    def to_report(self) -> str:
        """Generate a human-readable report."""
        lines = [
            "=" * 60,
            "SCHEMA EVALUATION REPORT",
            "=" * 60,
            "",
            f"Total Score: {self.total_score}/{self.max_possible_score} ({self.percentage:.1f}%)",
            "",
            "-" * 60,
            "SCORES BY AXIS",
            "-" * 60,
        ]

        for axis_name, score in self.axis_scores.items():
            lines.append(f"\n{axis_name.replace('_', ' ').title()}: {score.score}/{score.max_score}")
            if score.deductions:
                for ded in score.deductions:
                    lines.append(f"  - [{ded.severity.value.upper()}] {ded.reason} (-{ded.points})")
            if score.commentary:
                lines.append(f"  Commentary: {score.commentary}")

        if self.critique:
            lines.extend([
                "",
                "-" * 60,
                "CRITIQUE",
                "-" * 60,
                self.critique,
            ])

        if self.recommendations:
            lines.extend([
                "",
                "-" * 60,
                "RECOMMENDATIONS",
                "-" * 60,
            ])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
