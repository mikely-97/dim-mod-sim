"""Main Textual application for dim-mod-sim."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from dim_mod_sim.ui.screens.home import HomeScreen


class DimModSimApp(App):
    """Dimensional Modeling Simulation - Interactive TUI."""

    TITLE = "Dim-Mod-Sim"
    SUB_TITLE = "Dimensional Modeling Trainer"
    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("d", "toggle_dark", "Dark/Light", show=True),
    ]

    SCREENS = {
        "home": HomeScreen,
    }

    def compose(self) -> ComposeResult:
        """Create the main app layout."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on startup."""
        self.push_screen("home")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark

    def action_help(self) -> None:
        """Show help modal."""
        from dim_mod_sim.ui.modals.help import HelpModal
        self.push_screen(HelpModal())


def run() -> None:
    """Entry point for running the TUI."""
    app = DimModSimApp()
    app.run()


if __name__ == "__main__":
    run()
