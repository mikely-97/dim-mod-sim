"""Progress tracker for managing evaluation history."""

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from dim_mod_sim.evaluator.result import EvaluationResult
from dim_mod_sim.progress.models import ProgressStore, ScenarioProgress, compute_schema_hash


def get_default_progress_path() -> Path:
    """Get the default path for progress storage."""
    # Check environment variable first
    env_path = os.environ.get("DIM_MOD_SIM_PROGRESS_FILE")
    if env_path:
        return Path(env_path)

    # Default to ~/.dim-mod-sim/progress.json
    return Path.home() / ".dim-mod-sim" / "progress.json"


class ProgressTracker:
    """Tracks evaluation progress across sessions."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_default_progress_path()
        self.store = ProgressStore.load(self.path)

    def record_attempt(
        self,
        seed: int,
        difficulty: str,
        result: EvaluationResult,
        schema_dict: dict,
    ) -> tuple[bool, bool, bool]:
        """Record an evaluation attempt.

        Returns:
            Tuple of (is_improvement, is_regression, is_new_best).
        """
        schema_hash = compute_schema_hash(schema_dict)

        axis_scores = {
            name: score.score
            for name, score in result.axis_scores.items()
        }

        deduction_count = sum(
            len(score.deductions)
            for score in result.axis_scores.values()
        )

        is_improvement, is_regression, is_new_best = self.store.record_attempt(
            seed=seed,
            difficulty=difficulty,
            total_score=result.total_score,
            max_score=result.max_possible_score,
            axis_scores=axis_scores,
            deduction_count=deduction_count,
            schema_hash=schema_hash,
        )

        # Save after each attempt
        self.store.save(self.path)

        return is_improvement, is_regression, is_new_best

    def get_scenario(self, seed: int, difficulty: str) -> ScenarioProgress | None:
        """Get progress for a specific scenario."""
        return self.store.get_scenario(seed, difficulty)

    def display_progress(
        self,
        seed: int,
        difficulty: str,
        console: Console,
    ) -> None:
        """Display progress for a scenario."""
        scenario = self.get_scenario(seed, difficulty)

        if scenario is None or scenario.attempt_count == 0:
            console.print("[dim]No previous attempts for this scenario.[/dim]")
            return

        # Build progress display
        lines = [
            f"[bold]Best Score:[/bold] {scenario.best_score} ({scenario.best_percentage:.1f}%)",
            f"[bold]Attempts:[/bold] {scenario.attempt_count}",
            "",
        ]

        # Show attempt history (last 5)
        recent = scenario.attempts[-5:]
        lines.append("[bold]Recent History:[/bold]")

        for i, attempt in enumerate(recent):
            # Calculate relative index from the full list
            idx = scenario.attempt_count - len(recent) + i + 1
            pct = attempt.percentage

            # Progress bar
            bar_width = 20
            filled = int(pct / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)

            # Determine if this was an improvement
            marker = ""
            if idx > 1:
                prev = scenario.attempts[scenario.attempt_count - len(recent) + i - 1]
                if attempt.percentage > prev.percentage:
                    marker = " [green]+{:.0f}%[/green]".format(attempt.percentage - prev.percentage)
                elif attempt.percentage < prev.percentage:
                    marker = " [red]{:.0f}%[/red]".format(attempt.percentage - prev.percentage)

            if attempt.total_score == scenario.best_score:
                marker += " [bold yellow]BEST[/bold yellow]"

            lines.append(f"  #{idx}  {pct:5.1f}%  {bar}{marker}")

        # Time info
        if scenario.last_attempt:
            from datetime import datetime
            diff = datetime.now() - scenario.last_attempt
            if diff.days > 0:
                time_ago = f"{diff.days} days ago"
            elif diff.seconds > 3600:
                time_ago = f"{diff.seconds // 3600} hours ago"
            elif diff.seconds > 60:
                time_ago = f"{diff.seconds // 60} minutes ago"
            else:
                time_ago = "just now"
            lines.append(f"\n[dim]Last attempt: {time_ago}[/dim]")

        console.print(Panel(
            "\n".join(lines),
            title=f"[bold]Progress: Seed {seed}, {difficulty.title()}[/bold]",
            border_style="blue",
        ))

    def display_improvement(
        self,
        is_improvement: bool,
        is_regression: bool,
        is_new_best: bool,
        console: Console,
    ) -> None:
        """Display improvement/regression message."""
        if is_new_best:
            console.print("[bold green]★ NEW PERSONAL BEST! ★[/bold green]")
        elif is_improvement:
            console.print("[green]↑ Improvement from last attempt![/green]")
        elif is_regression:
            console.print("[yellow]↓ Regression from last attempt[/yellow]")
