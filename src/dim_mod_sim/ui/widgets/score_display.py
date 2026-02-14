"""Score display widget showing evaluation results."""

from textual.reactive import reactive
from textual.widgets import Static

from dim_mod_sim.evaluator.result import EvaluationResult


# Axis display names
AXIS_NAMES = {
    "event_preservation": "Event Preservation",
    "grain_correctness": "Grain Correctness",
    "temporal_correctness": "Temporal Correctness",
    "semantic_faithfulness": "Semantic Faithfulness",
    "structural_optimality": "Structural Optimality",
    "queryability": "Queryability",
}


class ScoreDisplay(Static):
    """Displays evaluation scores as horizontal progress bars."""

    CSS = """
    ScoreDisplay {
        height: auto;
        padding: 1;
        border: solid $primary-lighten-2;
        background: $surface;
    }
    """

    result: reactive[EvaluationResult | None] = reactive(None)

    def render(self) -> str:
        """Render the score display."""
        if not self.result:
            return "[dim]No evaluation yet. Click 'Evaluate' to score your schema.[/dim]"

        lines: list[str] = []

        # Overall score header
        pct = self.result.percentage
        color = self._score_color(pct)
        lines.append(
            f"[bold]SCORE: [{color}]{self.result.total_score}/{self.result.max_possible_score}[/{color}] "
            f"([{color}]{pct:.0f}%[/{color}])[/bold]"
        )
        lines.append("")

        # Individual axis scores
        for axis_name, score in self.result.axis_scores.items():
            display_name = AXIS_NAMES.get(axis_name, axis_name.replace("_", " ").title())
            axis_pct = score.percentage
            axis_color = self._score_color(axis_pct)

            # Create progress bar (20 chars wide)
            bar_width = 20
            filled = int(bar_width * axis_pct / 100)
            empty = bar_width - filled

            bar = f"[{axis_color}]{'█' * filled}[/{axis_color}][dim]{'░' * empty}[/dim]"

            # Deduction count indicator
            deductions = len(score.deductions)
            deduction_str = f" [dim]({deductions} issues)[/dim]" if deductions > 0 else ""

            lines.append(
                f"{display_name:<22} {bar} [{axis_color}]{axis_pct:>3.0f}%[/{axis_color}]{deduction_str}"
            )

        return "\n".join(lines)

    def _score_color(self, percentage: float) -> str:
        """Get color based on score percentage."""
        if percentage >= 75:
            return "green"
        elif percentage >= 50:
            return "yellow"
        else:
            return "red"

    def watch_result(self, result: EvaluationResult | None) -> None:
        """React to result changes."""
        self.refresh()


class ScoreSummary(Static):
    """Compact single-line score summary."""

    CSS = """
    ScoreSummary {
        height: 1;
        padding: 0 1;
        background: $primary-darken-2;
    }
    """

    result: reactive[EvaluationResult | None] = reactive(None)

    def render(self) -> str:
        """Render compact score summary."""
        if not self.result:
            return "[dim]Not evaluated[/dim]"

        pct = self.result.percentage
        color = "green" if pct >= 75 else "yellow" if pct >= 50 else "red"

        return (
            f"[bold]Score:[/bold] [{color}]{self.result.total_score}/{self.result.max_possible_score}[/{color}] "
            f"([{color}]{pct:.0f}%[/{color}])"
        )

    def watch_result(self, result: EvaluationResult | None) -> None:
        """React to result changes."""
        self.refresh()
