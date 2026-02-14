"""Widget for displaying enabled traps by category."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from dim_mod_sim.play.framing import DifficultyBriefing, EnabledTrap, TrapCategory


CATEGORY_COLORS = {
    TrapCategory.GRAIN: "red",
    TrapCategory.TEMPORAL: "yellow",
    TrapCategory.IDENTITY: "magenta",
    TrapCategory.SEMANTIC: "cyan",
    TrapCategory.RELATIONSHIP: "blue",
}

CATEGORY_ICONS = {
    TrapCategory.GRAIN: "#",
    TrapCategory.TEMPORAL: "@",
    TrapCategory.IDENTITY: "&",
    TrapCategory.SEMANTIC: "~",
    TrapCategory.RELATIONSHIP: "<>",
}


class TrapGrid(Static):
    """Displays enabled traps grouped by category with colors."""

    CSS = """
    TrapGrid {
        height: auto;
        padding: 1;
        border: solid $primary-lighten-2;
    }

    .trap-category {
        padding-bottom: 1;
    }

    .trap-category-header {
        text-style: bold;
    }

    .trap-item {
        padding-left: 2;
    }

    .no-traps {
        text-style: italic;
        color: $text-muted;
    }
    """

    briefing: reactive[DifficultyBriefing | None] = reactive(None)

    def render(self) -> str:
        """Render the trap grid."""
        if not self.briefing or not self.briefing.enabled_traps:
            return "[dim italic]No traps enabled - this should be straightforward![/dim italic]"

        lines: list[str] = []
        traps_by_cat = self.briefing.traps_by_category

        for category in TrapCategory:
            if category not in traps_by_cat:
                continue

            color = CATEGORY_COLORS.get(category, "white")
            icon = CATEGORY_ICONS.get(category, "*")
            traps = traps_by_cat[category]

            lines.append(f"[bold {color}]{icon} {category.value.upper()}[/bold {color}]")

            for trap in traps:
                lines.append(f"  [{color}]-[/{color}] {trap.name}")

            lines.append("")

        return "\n".join(lines).strip()

    def watch_briefing(self, briefing: DifficultyBriefing | None) -> None:
        """React to briefing changes."""
        self.refresh()


class TrapSummary(Static):
    """Compact summary of threats for the scenario."""

    CSS = """
    TrapSummary {
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border: dashed $warning;
    }
    """

    briefing: reactive[DifficultyBriefing | None] = reactive(None)

    def render(self) -> str:
        """Render threat summary."""
        if not self.briefing:
            return ""

        threats = self.briefing.threat_summary
        if not threats:
            return "[dim]This shop plays nice.[/dim]"

        lines = [f"[bold]This shop will try to break your model by:[/bold]"]
        for threat in threats:
            lines.append(f"  [dim]-[/dim] {threat}")

        return "\n".join(lines)

    def watch_briefing(self, briefing: DifficultyBriefing | None) -> None:
        """React to briefing changes."""
        self.refresh()
