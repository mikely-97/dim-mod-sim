"""JSON schema editor widget with validation."""

import json
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static, TextArea


class SchemaEditor(Vertical):
    """JSON editor with live validation for dimensional schemas."""

    CSS = """
    SchemaEditor {
        height: 1fr;
    }

    #editor-area {
        height: 1fr;
        border: solid $primary-lighten-2;
    }

    #validation-status {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
    }

    .validation-ok {
        color: $success;
    }

    .validation-error {
        color: $error;
    }

    .validation-warning {
        color: $warning;
    }
    """

    schema_text: reactive[str] = reactive("{}")
    is_valid: reactive[bool] = reactive(False)
    validation_message: reactive[str] = reactive("")

    def __init__(
        self,
        initial_content: str = "{}",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.schema_text = initial_content

    def compose(self) -> ComposeResult:
        """Create the editor layout."""
        yield TextArea(
            self.schema_text,
            language="json",
            theme="monokai",
            id="editor-area",
            show_line_numbers=True,
        )
        yield Static("", id="validation-status")

    def on_mount(self) -> None:
        """Initialize validation on mount."""
        self._validate_content(self.schema_text)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text changes and validate."""
        self.schema_text = event.text_area.text
        self._validate_content(self.schema_text)

    def _validate_content(self, content: str) -> None:
        """Validate JSON content and update status."""
        status = self.query_one("#validation-status", Static)

        # First check if it's valid JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            self.is_valid = False
            self.validation_message = f"JSON Error: {e.msg} (line {e.lineno})"
            status.update(f"[red]X[/red] {self.validation_message}")
            status.remove_class("validation-ok", "validation-warning")
            status.add_class("validation-error")
            return

        # Check if it has the basic structure
        if not isinstance(data, dict):
            self.is_valid = False
            self.validation_message = "Schema must be a JSON object"
            status.update(f"[red]X[/red] {self.validation_message}")
            status.remove_class("validation-ok", "validation-warning")
            status.add_class("validation-error")
            return

        # Check for required keys
        required_keys = {"fact_tables", "dimension_tables"}
        present_keys = set(data.keys())
        missing_keys = required_keys - present_keys

        if missing_keys:
            self.is_valid = False
            self.validation_message = f"Missing required keys: {', '.join(missing_keys)}"
            status.update(f"[yellow]![/yellow] {self.validation_message}")
            status.remove_class("validation-ok", "validation-error")
            status.add_class("validation-warning")
            return

        # Count tables
        fact_count = len(data.get("fact_tables", []))
        dim_count = len(data.get("dimension_tables", []))
        rel_count = len(data.get("relationships", []))

        self.is_valid = True
        self.validation_message = f"Valid: {fact_count} facts, {dim_count} dimensions, {rel_count} relationships"
        status.update(f"[green]OK[/green] {self.validation_message}")
        status.remove_class("validation-error", "validation-warning")
        status.add_class("validation-ok")

    def set_content(self, content: str) -> None:
        """Set the editor content programmatically."""
        editor = self.query_one("#editor-area", TextArea)
        editor.load_text(content)
        self.schema_text = content
        self._validate_content(content)

    def get_content(self) -> str:
        """Get the current editor content."""
        editor = self.query_one("#editor-area", TextArea)
        return editor.text

    def get_parsed_schema(self) -> dict[str, Any] | None:
        """Get the parsed schema if valid, None otherwise."""
        try:
            return json.loads(self.schema_text)
        except json.JSONDecodeError:
            return None
