"""New game modal for difficulty and seed selection."""

import random

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from dim_mod_sim.shop.options import Difficulty


class NewGameModal(ModalScreen[tuple[Difficulty, int] | None]):
    """Modal for selecting difficulty and seed for a new game."""

    CSS = """
    NewGameModal {
        align: center middle;
    }

    #new-game-dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        border: round $primary;
        background: $surface;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    .section-label {
        padding-top: 1;
        text-style: bold;
        color: $text-muted;
    }

    #seed-input {
        margin-top: 1;
    }

    #button-row {
        margin-top: 2;
        align: center middle;
        height: auto;
    }

    #button-row Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="new-game-dialog"):
            yield Static("New Game", id="dialog-title")

            yield Label("Difficulty", classes="section-label")
            with RadioSet(id="difficulty-select"):
                yield RadioButton("Easy", id="diff-easy", value=True)
                yield RadioButton("Medium", id="diff-medium")
                yield RadioButton("Hard", id="diff-hard")
                yield RadioButton("Adversarial", id="diff-adversarial")

            yield Label("Seed (optional)", classes="section-label")
            yield Input(
                placeholder="Leave blank for random",
                id="seed-input",
                type="integer",
            )

            with Horizontal(id="button-row"):
                yield Button("Start", id="btn-start", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-start":
            self._start_game()

    def _start_game(self) -> None:
        """Gather selections and dismiss with result."""
        # Get difficulty from radio set
        radio_set = self.query_one("#difficulty-select", RadioSet)
        difficulty_map = {
            "diff-easy": Difficulty.EASY,
            "diff-medium": Difficulty.MEDIUM,
            "diff-hard": Difficulty.HARD,
            "diff-adversarial": Difficulty.ADVERSARIAL,
        }

        difficulty = Difficulty.MEDIUM  # Default
        if radio_set.pressed_button:
            btn_id = radio_set.pressed_button.id
            if btn_id in difficulty_map:
                difficulty = difficulty_map[btn_id]

        # Get seed
        seed_input = self.query_one("#seed-input", Input)
        seed_value = seed_input.value.strip()

        if seed_value:
            try:
                seed = int(seed_value)
            except ValueError:
                self.notify("Invalid seed - must be a number", severity="error")
                return
        else:
            seed = random.randint(0, 2**31 - 1)

        self.dismiss((difficulty, seed))
