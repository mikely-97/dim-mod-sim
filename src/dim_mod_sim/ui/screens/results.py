"""Results screen - final evaluation breakdown with export options."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

from dim_mod_sim.evaluator.feedback import ActionableFeedback
from dim_mod_sim.evaluator.result import EvaluationResult
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import Difficulty


class ResultsScreen(Screen):
    """Screen showing final evaluation results with export options."""

    CSS = """
    ResultsScreen {
        layout: vertical;
    }

    #results-header {
        height: 7;
        padding: 1 2;
        background: $primary-darken-2;
        align: center middle;
    }

    #score-display {
        text-align: center;
        text-style: bold;
    }

    #subtitle {
        text-align: center;
        color: $text-muted;
    }

    #main-content {
        height: 1fr;
        padding: 1;
    }

    #axis-panel {
        width: 1fr;
        padding: 1;
        border: solid $primary-lighten-2;
    }

    #summary-panel {
        width: 1fr;
        padding: 1;
        border: solid $primary-lighten-2;
        margin-left: 1;
    }

    .axis-row {
        height: 2;
    }

    #button-bar {
        height: 5;
        align: center middle;
        padding: 1;
        dock: bottom;
        background: $surface-darken-1;
    }

    #button-bar Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("r", "retry", "Try Again"),
        ("n", "new_game", "New Game"),
    ]

    def __init__(
        self,
        result: EvaluationResult,
        config: ShopConfiguration,
        difficulty: Difficulty,
        seed: int,
        output_dir: Path,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self.result = result
        self.config = config
        self.difficulty = difficulty
        self.seed = seed
        self.output_dir = output_dir
        self.feedback = ActionableFeedback.from_result(result)

    def compose(self) -> ComposeResult:
        """Create the results screen layout."""
        yield Header()

        # Results header with big score
        pct = self.result.percentage
        color = "green" if pct >= 75 else "yellow" if pct >= 50 else "red"

        with Vertical(id="results-header"):
            yield Static(
                f"[{color} bold]FINAL SCORE: {self.result.total_score}/{self.result.max_possible_score}[/{color} bold]",
                id="score-display",
            )
            yield Static(
                f"[{color}]{pct:.1f}%[/{color}] | {self.config.shop_name} | Seed: {self.seed}",
                id="subtitle",
            )

        # Main content
        with Horizontal(id="main-content"):
            # Axis breakdown
            with VerticalScroll(id="axis-panel"):
                yield Static("[bold]Score Breakdown[/bold]")
                yield Static("")
                yield Static(self._render_axis_scores())

            # Summary and recommendations
            with VerticalScroll(id="summary-panel"):
                yield Static("[bold]Summary[/bold]")
                yield Static("")
                yield Markdown(self._generate_summary_markdown())

        # Button bar
        with Horizontal(id="button-bar"):
            yield Button("Try Again", id="btn-retry", variant="primary")
            yield Button("New Game", id="btn-new", variant="default")
            yield Button("Export Report", id="btn-export", variant="default")
            yield Button("Home", id="btn-home", variant="default")

        yield Footer()

    def _render_axis_scores(self) -> str:
        """Render axis scores as text."""
        lines = []
        axis_names = {
            "event_preservation": "Event Preservation",
            "grain_correctness": "Grain Correctness",
            "temporal_correctness": "Temporal Correctness",
            "semantic_faithfulness": "Semantic Faithfulness",
            "structural_optimality": "Structural Optimality",
            "queryability": "Queryability",
        }

        for axis_name, score in self.result.axis_scores.items():
            display_name = axis_names.get(axis_name, axis_name)
            pct = score.percentage
            color = "green" if pct >= 75 else "yellow" if pct >= 50 else "red"

            bar_width = 25
            filled = int(bar_width * pct / 100)
            bar = f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (bar_width - filled)}[/dim]"

            issues = len(score.deductions)
            issue_str = f" [dim]({issues} issues)[/dim]" if issues > 0 else ""

            lines.append(f"{display_name:<22}")
            lines.append(f"  {bar} [{color}]{pct:>3.0f}%[/{color}]{issue_str}")
            lines.append("")

        return "\n".join(lines)

    def _generate_summary_markdown(self) -> str:
        """Generate summary as markdown."""
        lines = []

        # Overall assessment
        pct = self.result.percentage
        if pct >= 90:
            lines.append("**Excellent!** Your schema handles this scenario well.")
        elif pct >= 75:
            lines.append("**Good job!** A few improvements would make it even better.")
        elif pct >= 50:
            lines.append("**Getting there.** Several issues need attention.")
        else:
            lines.append("**Needs work.** Review the traps and feedback carefully.")

        lines.append("")

        # Top issues
        if self.feedback.violations:
            lines.append("### Top Issues")
            for v in self.feedback.violations[:3]:
                lines.append(f"- **{v.violation_type.value}**: {v.what_went_wrong[:60]}...")

        lines.append("")

        # Fix priority
        if self.feedback.fix_priority:
            lines.append("### Fix Priority")
            for i, fix in enumerate(self.feedback.fix_priority[:5], 1):
                lines.append(f"{i}. {fix}")

        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-retry":
            self.action_retry()
        elif button_id == "btn-new":
            self.action_new_game()
        elif button_id == "btn-export":
            self._export_report()
        elif button_id == "btn-home":
            self._go_home()

    def action_retry(self) -> None:
        """Go back to play screen to try again."""
        # Pop results, stay on play screen
        self.app.pop_screen()

    def action_new_game(self) -> None:
        """Start a new game."""
        # Pop back to home and trigger new game
        self._go_home()

    def _go_home(self) -> None:
        """Return to home screen."""
        # Pop all screens back to home
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()

    def _export_report(self) -> None:
        """Export evaluation report to file."""
        report = self._generate_report()
        report_path = self.output_dir / f"report_seed{self.seed}.md"

        try:
            with open(report_path, "w") as f:
                f.write(report)
            self.notify(f"Report exported to {report_path}", title="Export Complete")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    def _generate_report(self) -> str:
        """Generate full markdown report."""
        lines = [
            f"# Dim-Mod-Sim Evaluation Report",
            "",
            f"**Shop:** {self.config.shop_name}",
            f"**Seed:** {self.seed}",
            f"**Difficulty:** {self.difficulty.value.title()}",
            "",
            f"## Final Score: {self.result.total_score}/{self.result.max_possible_score} ({self.result.percentage:.1f}%)",
            "",
            "## Axis Breakdown",
            "",
            "| Axis | Score | Percentage | Issues |",
            "|------|-------|------------|--------|",
        ]

        axis_names = {
            "event_preservation": "Event Preservation",
            "grain_correctness": "Grain Correctness",
            "temporal_correctness": "Temporal Correctness",
            "semantic_faithfulness": "Semantic Faithfulness",
            "structural_optimality": "Structural Optimality",
            "queryability": "Queryability",
        }

        for axis_name, score in self.result.axis_scores.items():
            display_name = axis_names.get(axis_name, axis_name)
            lines.append(
                f"| {display_name} | {score.score}/{score.max_score} | "
                f"{score.percentage:.0f}% | {len(score.deductions)} |"
            )

        lines.append("")
        lines.append("## Issues Found")
        lines.append("")

        for v in self.feedback.violations:
            lines.append(f"### {v.violation_type.value.replace('_', ' ').title()}")
            lines.append("")
            lines.append(f"**What went wrong:** {v.what_went_wrong}")
            lines.append("")
            if v.concrete_example:
                lines.append(f"**Example:** {v.concrete_example}")
                lines.append("")
            if v.consequence:
                lines.append(f"**Consequence:** {v.consequence}")
                lines.append("")
            if v.fix_hint:
                lines.append(f"**Fix:** {v.fix_hint}")
                lines.append("")

        lines.append("---")
        lines.append("*Generated by Dim-Mod-Sim*")

        return "\n".join(lines)

    def action_go_back(self) -> None:
        """Go back to play screen."""
        self.app.pop_screen()
