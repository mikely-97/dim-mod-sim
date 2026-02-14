"""Help modal showing keyboard shortcuts and usage."""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Markdown, Static


HELP_CONTENT = """
## Global Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `?` | Show this help |
| `d` | Toggle dark/light mode |
| `Escape` | Go back / Close modal |

## Play Screen

| Key | Action |
|-----|--------|
| `Ctrl+E` | Evaluate schema |
| `Ctrl+S` | Save schema to file |
| `Ctrl+L` | Load scaffold |

## Navigation

- Use `Tab` to move between widgets
- Use `Enter` to activate buttons
- Use arrow keys to navigate lists and trees

## Schema Editor

- Full JSON syntax highlighting
- Live validation as you type
- Error messages in status bar

## Evaluation Feedback

- Click violation categories to expand/collapse
- Violations sorted by severity (critical first)
- Fix hints provided for each issue

## Tips

1. **Start with scaffold**: Use "Load Scaffold" to get a starting template
2. **Iterate**: Evaluate often to catch issues early
3. **Read the traps**: Pay attention to enabled traps in scenario screen
4. **Check all axes**: Balance your design across all 6 evaluation axes
"""


class HelpModal(ModalScreen[None]):
    """Modal showing keyboard shortcuts and help."""

    CSS = """
    HelpModal {
        align: center middle;
    }

    #help-dialog {
        width: 65;
        height: 80%;
        padding: 1 2;
        border: round $primary;
        background: $surface;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    #help-content {
        height: 1fr;
        padding: 1;
    }

    #close-button {
        dock: bottom;
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="help-dialog"):
            yield Static("Keyboard Shortcuts & Help", id="help-title")
            with VerticalScroll(id="help-content"):
                yield Markdown(HELP_CONTENT)
            yield Button("Close", id="close-button", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle close button."""
        self.dismiss(None)

    def key_escape(self) -> None:
        """Close on escape."""
        self.dismiss(None)
