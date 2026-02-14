"""Home screen - landing page with navigation options."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

from dim_mod_sim.description.generator import DescriptionGenerator
from dim_mod_sim.progress.tracker import ProgressTracker
from dim_mod_sim.shop.generator import ShopGenerator
from dim_mod_sim.shop.options import Difficulty
from dim_mod_sim.ui.modals.new_game import NewGameModal


class HomeScreen(Screen):
    """Main landing screen with navigation to key features."""

    DEFAULT_OUTPUT_DIR = Path("./output")

    def compose(self) -> ComposeResult:
        """Create the home screen layout."""
        with Container(id="home-container"):
            yield Static("Dim-Mod-Sim", id="app-title")
            yield Static("Master Dimensional Modeling", id="app-subtitle")

            with Vertical(id="button-container"):
                yield Button(
                    "New Game",
                    id="btn-new-game",
                    classes="home-button -primary",
                    variant="primary",
                )
                yield Button(
                    "Continue",
                    id="btn-continue",
                    classes="home-button",
                    variant="default",
                )
                yield Button(
                    "Progress",
                    id="btn-progress",
                    classes="home-button",
                    variant="default",
                )
                yield Button(
                    "Quit",
                    id="btn-quit",
                    classes="home-button",
                    variant="error",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-new-game":
            self.app.push_screen(NewGameModal(), self._on_new_game_result)

        elif button_id == "btn-continue":
            self._continue_last_scenario()

        elif button_id == "btn-progress":
            from dim_mod_sim.ui.screens.progress import ProgressScreen
            self.app.push_screen(ProgressScreen())

        elif button_id == "btn-quit":
            self.app.exit()

    def _on_new_game_result(
        self, result: tuple[Difficulty, int] | None
    ) -> None:
        """Handle result from NewGameModal."""
        if result is None:
            # User cancelled
            return

        difficulty, seed = result
        self._start_new_game(difficulty, seed)

    def _start_new_game(self, difficulty: Difficulty, seed: int) -> None:
        """Generate scenario and navigate to ScenarioScreen."""
        # Show loading indicator
        self.notify(f"Generating {difficulty.value} scenario (seed: {seed})...", title="Loading")

        # Generate shop configuration
        shop_gen = ShopGenerator(seed, difficulty)
        config = shop_gen.generate()

        # Generate description
        desc_gen = DescriptionGenerator(config)
        description = desc_gen.generate()

        # Ensure output directory exists
        output_dir = self.DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        # Import here to avoid circular import
        from dim_mod_sim.ui.screens.scenario import ScenarioScreen

        # Push scenario screen
        self.app.push_screen(
            ScenarioScreen(
                config=config,
                difficulty=difficulty,
                seed=seed,
                description=description,
                output_dir=output_dir,
            )
        )

    def _continue_last_scenario(self) -> None:
        """Continue the most recently played scenario."""
        from datetime import datetime

        tracker = ProgressTracker()

        if not tracker.store.scenarios:
            self.notify("No previous games found. Start a new game!", severity="warning")
            return

        # Find most recent scenario
        most_recent = max(
            tracker.store.scenarios.values(),
            key=lambda s: s.last_attempt or datetime.min,
        )

        # Start the game with that seed and difficulty
        try:
            difficulty = Difficulty(most_recent.difficulty)
        except ValueError:
            difficulty = Difficulty.MEDIUM

        self._start_new_game(difficulty, most_recent.seed)
