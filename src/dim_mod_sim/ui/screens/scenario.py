"""Scenario briefing screen - shows business description and enabled traps."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

from dim_mod_sim.play.briefing import BriefingGenerator
from dim_mod_sim.play.framing import DifficultyBriefing
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import Difficulty
from dim_mod_sim.ui.widgets.trap_grid import TrapGrid, TrapSummary


class ScenarioScreen(Screen):
    """Screen showing scenario briefing before play begins."""

    CSS = """
    ScenarioScreen {
        layout: vertical;
    }

    #scenario-header {
        height: 5;
        padding: 1 2;
        background: $primary-darken-2;
    }

    #header-title {
        text-style: bold;
        text-align: center;
    }

    #header-meta {
        text-align: center;
        color: $text-muted;
    }

    #main-content {
        height: 1fr;
    }

    #description-panel {
        width: 2fr;
        padding: 1;
        border: solid $primary-lighten-2;
        margin: 1;
    }

    #traps-panel {
        width: 1fr;
        padding: 1;
        margin: 1;
    }

    #tagline {
        text-style: bold italic;
        text-align: center;
        padding: 1;
        color: $warning;
    }

    #button-bar {
        height: 5;
        align: center middle;
        padding: 1;
        dock: bottom;
    }

    #button-bar Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("enter", "start_modeling", "Start"),
    ]

    def __init__(
        self,
        config: ShopConfiguration,
        difficulty: Difficulty,
        seed: int,
        description: str,
        output_dir: Path,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self.config = config
        self.difficulty = difficulty
        self.seed = seed
        self.description = description
        self.output_dir = output_dir

        # Generate briefing
        briefing_gen = BriefingGenerator(config, difficulty)
        self.briefing = briefing_gen.generate()

    def compose(self) -> ComposeResult:
        """Create the scenario screen layout."""
        yield Header()

        # Scenario header
        with Vertical(id="scenario-header"):
            yield Static(
                f"{self.briefing.difficulty_name} SCENARIO",
                id="header-title",
            )
            yield Static(
                f"Seed: {self.seed}  |  Shop: {self.config.shop_name}",
                id="header-meta",
            )

        # Tagline
        yield Static(self.briefing.adversarial_tagline, id="tagline")

        # Main content: description + traps side by side
        with Horizontal(id="main-content"):
            with ScrollableContainer(id="description-panel"):
                yield Markdown(self.description)

            with Vertical(id="traps-panel"):
                trap_grid = TrapGrid()
                trap_grid.briefing = self.briefing
                yield trap_grid

                trap_summary = TrapSummary()
                trap_summary.briefing = self.briefing
                yield trap_summary

        # Button bar
        with Horizontal(id="button-bar"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Start Modeling", id="btn-start", variant="primary")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-start":
            self.action_start_modeling()

    def action_go_back(self) -> None:
        """Return to home screen."""
        self.app.pop_screen()

    def action_start_modeling(self) -> None:
        """Proceed to the play screen."""
        from dim_mod_sim.ui.screens.play import PlayScreen

        self.app.push_screen(
            PlayScreen(
                config=self.config,
                difficulty=self.difficulty,
                seed=self.seed,
                output_dir=self.output_dir,
            )
        )
