"""Progress screen - shows historical attempts and scores."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static

from dim_mod_sim.progress.tracker import ProgressTracker


class ProgressScreen(Screen):
    """Screen showing progress history across all scenarios."""

    CSS = """
    ProgressScreen {
        layout: vertical;
    }

    #progress-header {
        height: 5;
        padding: 1 2;
        background: $primary-darken-2;
    }

    #header-title {
        text-style: bold;
        text-align: center;
    }

    #header-stats {
        text-align: center;
        color: $text-muted;
    }

    #main-content {
        height: 1fr;
        padding: 1;
    }

    #scenario-table {
        height: 1fr;
        border: solid $primary-lighten-2;
    }

    #detail-panel {
        height: 15;
        padding: 1;
        border: solid $primary-lighten-2;
        margin-top: 1;
    }

    #button-bar {
        height: 5;
        align: center middle;
        padding: 1;
        dock: bottom;
    }

    #button-bar Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name=name)
        self.tracker = ProgressTracker()
        self.selected_scenario: str | None = None

    def compose(self) -> ComposeResult:
        """Create the progress screen layout."""
        yield Header()

        # Header
        with Vertical(id="progress-header"):
            yield Static("Progress Dashboard", id="header-title")
            yield Static(self._get_stats_summary(), id="header-stats")

        # Main content
        with Vertical(id="main-content"):
            # Scenario table
            table = DataTable(id="scenario-table")
            table.cursor_type = "row"
            table.zebra_stripes = True
            yield table

            # Detail panel
            yield Static("Select a scenario to see details", id="detail-panel")

        # Button bar
        with Horizontal(id="button-bar"):
            yield Button("Continue Selected", id="btn-continue", variant="primary")
            yield Button("Back", id="btn-back", variant="default")

        yield Footer()

    def on_mount(self) -> None:
        """Populate table on mount."""
        table = self.query_one("#scenario-table", DataTable)

        # Add columns
        table.add_column("Seed", key="seed")
        table.add_column("Difficulty", key="difficulty")
        table.add_column("Best", key="best")
        table.add_column("Attempts", key="attempts")
        table.add_column("Last Played", key="last")

        # Add rows
        for key, scenario in sorted(
            self.tracker.store.scenarios.items(),
            key=lambda x: x[1].last_attempt or datetime.min,
            reverse=True,
        ):
            pct = scenario.best_percentage
            color = "green" if pct >= 75 else "yellow" if pct >= 50 else "red"

            last_str = ""
            if scenario.last_attempt:
                diff = datetime.now() - scenario.last_attempt
                if diff.days > 0:
                    last_str = f"{diff.days}d ago"
                elif diff.seconds > 3600:
                    last_str = f"{diff.seconds // 3600}h ago"
                elif diff.seconds > 60:
                    last_str = f"{diff.seconds // 60}m ago"
                else:
                    last_str = "just now"

            table.add_row(
                str(scenario.seed),
                scenario.difficulty.title(),
                f"[{color}]{scenario.best_score} ({pct:.0f}%)[/{color}]",
                str(scenario.attempt_count),
                last_str,
                key=key,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        self.selected_scenario = str(event.row_key.value) if event.row_key else None
        self._update_detail_panel()

    def _update_detail_panel(self) -> None:
        """Update the detail panel with selected scenario info."""
        panel = self.query_one("#detail-panel", Static)

        if not self.selected_scenario:
            panel.update("Select a scenario to see details")
            return

        scenario = self.tracker.store.scenarios.get(self.selected_scenario)
        if not scenario:
            panel.update("Scenario not found")
            return

        # Build detail view
        lines = [
            f"[bold]Seed {scenario.seed} - {scenario.difficulty.title()}[/bold]",
            "",
            f"Best Score: [green]{scenario.best_score}[/green] ({scenario.best_percentage:.1f}%)",
            f"Total Attempts: {scenario.attempt_count}",
            "",
            "[bold]Recent Attempts:[/bold]",
        ]

        for i, attempt in enumerate(reversed(scenario.attempts[-5:])):
            idx = scenario.attempt_count - i
            pct = attempt.percentage
            color = "green" if pct >= 75 else "yellow" if pct >= 50 else "red"
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            marker = " [yellow]★[/yellow]" if attempt.total_score == scenario.best_score else ""
            lines.append(f"  #{idx}: [{color}]{bar} {pct:.0f}%[/{color}]{marker}")

        panel.update("\n".join(lines))

    def _get_stats_summary(self) -> str:
        """Get summary statistics."""
        scenarios = self.tracker.store.scenarios
        if not scenarios:
            return "No progress recorded yet"

        total_attempts = sum(s.attempt_count for s in scenarios.values())
        best_scores = [s.best_percentage for s in scenarios.values()]
        avg_best = sum(best_scores) / len(best_scores) if best_scores else 0

        return f"{len(scenarios)} scenarios | {total_attempts} total attempts | Avg best: {avg_best:.0f}%"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-continue":
            self._continue_selected()

    def _continue_selected(self) -> None:
        """Continue the selected scenario."""
        if not self.selected_scenario:
            self.notify("No scenario selected", severity="warning")
            return

        scenario = self.tracker.store.scenarios.get(self.selected_scenario)
        if not scenario:
            self.notify("Scenario not found", severity="error")
            return

        # TODO: Load the scenario and push to ScenarioScreen
        self.notify(
            f"Continue seed {scenario.seed} ({scenario.difficulty}) - Coming soon!",
            title="Continue"
        )

    def action_go_back(self) -> None:
        """Return to home screen."""
        self.app.pop_screen()
