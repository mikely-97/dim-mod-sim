"""Main schema evaluation engine."""

from dim_mod_sim.events.models import EventLog
from dim_mod_sim.evaluator.axes import (
    EvaluationAxis,
    EvaluationContext,
    EventPreservationAxis,
    GrainCorrectnessAxis,
    QueryabilityAxis,
    SemanticFaithfulnessAxis,
    StructuralOptimalityAxis,
    TemporalCorrectnessAxis,
)
from dim_mod_sim.evaluator.result import AxisScore, EvaluationResult
from dim_mod_sim.schema.models import SchemaSubmission
from dim_mod_sim.shop.config import ShopConfiguration


class SchemaEvaluator:
    """Main evaluation engine for schema submissions."""

    def __init__(
        self,
        config: ShopConfiguration,
        events: EventLog,
        description: str | None = None,
    ) -> None:
        self.config = config
        self.events = events
        self.description = description

        # Build evaluation context
        self.context = EvaluationContext(config=config, events=events)

        # Initialize evaluation axes
        self.axes: list[EvaluationAxis] = [
            EventPreservationAxis(self.context),
            GrainCorrectnessAxis(self.context),
            TemporalCorrectnessAxis(self.context),
            SemanticFaithfulnessAxis(self.context),
            StructuralOptimalityAxis(self.context),
            QueryabilityAxis(self.context),
        ]

    def evaluate(self, submission: SchemaSubmission) -> EvaluationResult:
        """Evaluate a schema submission."""
        axis_scores: dict[str, AxisScore] = {}

        for axis in self.axes:
            score = axis.evaluate(submission)
            axis_scores[axis.name] = score

        total_score = sum(s.score for s in axis_scores.values())
        max_score = sum(s.max_score for s in axis_scores.values())

        critique = self._generate_critique(axis_scores, submission)
        recommendations = self._generate_recommendations(axis_scores)

        return EvaluationResult(
            total_score=total_score,
            max_possible_score=max_score,
            axis_scores=axis_scores,
            critique=critique,
            recommendations=recommendations,
        )

    def _generate_critique(
        self,
        axis_scores: dict[str, AxisScore],
        submission: SchemaSubmission,
    ) -> str:
        """Generate a written critique explaining the evaluation."""
        lines = []

        # Overview
        total_pct = sum(s.score for s in axis_scores.values()) / sum(s.max_score for s in axis_scores.values()) * 100
        if total_pct >= 80:
            lines.append("This schema demonstrates strong modeling practices overall.")
        elif total_pct >= 60:
            lines.append("This schema shows reasonable modeling but has areas for improvement.")
        elif total_pct >= 40:
            lines.append("This schema has significant issues that may cause problems in production.")
        else:
            lines.append("This schema has critical deficiencies that need to be addressed.")

        lines.append("")

        # Critical issues
        critical_issues = []
        for axis_name, score in axis_scores.items():
            for ded in score.deductions:
                if ded.severity.value == "critical":
                    critical_issues.append((axis_name, ded))

        if critical_issues:
            lines.append("**Critical Issues:**")
            for axis_name, ded in critical_issues:
                lines.append(f"- [{axis_name}] {ded.reason}")
            lines.append("")

        # Major issues
        major_issues = []
        for axis_name, score in axis_scores.items():
            for ded in score.deductions:
                if ded.severity.value == "major":
                    major_issues.append((axis_name, ded))

        if major_issues:
            lines.append("**Major Issues:**")
            for axis_name, ded in major_issues:
                lines.append(f"- [{axis_name}] {ded.reason}")
            lines.append("")

        # Strengths
        strong_axes = [
            name for name, score in axis_scores.items()
            if score.percentage >= 80
        ]
        if strong_axes:
            lines.append("**Strengths:**")
            for axis in strong_axes:
                lines.append(f"- {axis.replace('_', ' ').title()}: {axis_scores[axis].percentage:.0f}%")
            lines.append("")

        # Schema summary
        lines.append("**Schema Summary:**")
        lines.append(f"- {len(submission.fact_tables)} fact table(s)")
        lines.append(f"- {len(submission.dimension_tables)} dimension table(s)")
        lines.append(f"- {len(submission.relationships)} relationship(s)")
        if submission.bridge_tables:
            lines.append(f"- {len(submission.bridge_tables)} bridge table(s)")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        axis_scores: dict[str, AxisScore],
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Prioritize by worst-scoring axes
        sorted_axes = sorted(
            axis_scores.items(),
            key=lambda x: x[1].percentage,
        )

        for axis_name, score in sorted_axes:
            if score.percentage < 70:
                # Get the most impactful deduction
                critical_deds = [d for d in score.deductions if d.severity.value == "critical"]
                major_deds = [d for d in score.deductions if d.severity.value == "major"]

                if critical_deds:
                    ded = critical_deds[0]
                    recommendations.append(f"[{axis_name}] Fix critical issue: {ded.reason}")
                elif major_deds:
                    ded = major_deds[0]
                    recommendations.append(f"[{axis_name}] Address: {ded.reason}")

        # Add general recommendations based on config
        if self.config.time.backdated_corrections:
            recommendations.append(
                "Ensure fact tables distinguish event_timestamp from business_effective_date"
            )

        if self.config.transactions.grain.value == "mixed":
            recommendations.append(
                "Consider separate fact tables for line-item vs aggregated transactions"
            )

        return recommendations[:5]  # Top 5 recommendations
