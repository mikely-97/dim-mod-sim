"""Feedback tree widget for displaying grouped violations."""

from textual.reactive import reactive
from textual.widgets import Tree

from dim_mod_sim.evaluator.feedback import ActionableFeedback, ConcreteViolation, ViolationType


# Category colors and labels
VIOLATION_STYLES = {
    ViolationType.GRAIN_VIOLATION: ("red", "GRAIN"),
    ViolationType.TEMPORAL_LIE: ("yellow", "TEMPORAL"),
    ViolationType.SEMANTIC_MISMATCH: ("magenta", "SEMANTIC"),
    ViolationType.DATA_LOSS: ("red", "DATA LOSS"),
    ViolationType.FAN_OUT_RISK: ("red", "FAN-OUT"),
    ViolationType.OVER_MODELING: ("cyan", "OVER-MODEL"),
    ViolationType.UNDER_MODELING: ("blue", "UNDER-MODEL"),
}

SEVERITY_ICONS = {
    "critical": "[red bold]!!![/red bold]",
    "major": "[yellow bold]!![/yellow bold]",
    "moderate": "[yellow]![/yellow]",
    "minor": "[dim].[/dim]",
}


class FeedbackTree(Tree):
    """Tree widget displaying violations grouped by category."""

    CSS = """
    FeedbackTree {
        height: 1fr;
        border: solid $primary-lighten-2;
        background: $surface;
        scrollbar-gutter: stable;
    }
    """

    feedback: reactive[ActionableFeedback | None] = reactive(None)

    def __init__(
        self,
        label: str = "Feedback",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(label, name=name, id=id, classes=classes)
        self.show_root = False

    def watch_feedback(self, feedback: ActionableFeedback | None) -> None:
        """Rebuild tree when feedback changes."""
        self.clear()

        if not feedback:
            self.root.add_leaf("[dim]No feedback yet[/dim]")
            return

        if not feedback.violations:
            self.root.add_leaf("[green]No violations found![/green]")
            return

        # Group violations by category
        for vtype, violations in feedback.by_category.items():
            if not violations:
                continue

            color, label = VIOLATION_STYLES.get(vtype, ("white", vtype.value.upper()))

            # Add category node
            category_node = self.root.add(
                f"[{color} bold]{label}[/{color} bold] ({len(violations)})",
                expand=True,
            )

            # Add individual violations
            for v in violations:
                severity_icon = SEVERITY_ICONS.get(v.severity.value, "")
                violation_node = category_node.add(
                    f"{severity_icon} {v.what_went_wrong[:60]}{'...' if len(v.what_went_wrong) > 60 else ''}"
                )

                # Add details as leaves
                if v.concrete_example:
                    violation_node.add_leaf(f"[dim]Example:[/dim] {v.concrete_example[:80]}...")

                if v.consequence:
                    violation_node.add_leaf(f"[dim]Consequence:[/dim] {v.consequence[:80]}...")

                if v.fix_hint:
                    violation_node.add_leaf(f"[green]Fix:[/green] {v.fix_hint}")

                if v.affected_tables:
                    violation_node.add_leaf(f"[dim]Affects:[/dim] {', '.join(v.affected_tables)}")

        # Add fix priority at the end
        if feedback.fix_priority:
            priority_node = self.root.add("[bold]FIX PRIORITY[/bold]", expand=True)
            for i, fix in enumerate(feedback.fix_priority, 1):
                priority_node.add_leaf(f"{i}. {fix}")


class FeedbackSummary(Tree):
    """Compact feedback summary showing just counts and top issues."""

    CSS = """
    FeedbackSummary {
        height: auto;
        max-height: 15;
        border: solid $warning;
        background: $surface-darken-1;
    }
    """

    feedback: reactive[ActionableFeedback | None] = reactive(None)

    def __init__(
        self,
        label: str = "Issues",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(label, name=name, id=id, classes=classes)
        self.show_root = False

    def watch_feedback(self, feedback: ActionableFeedback | None) -> None:
        """Rebuild summary when feedback changes."""
        self.clear()

        if not feedback or not feedback.violations:
            self.root.add_leaf("[green]No issues[/green]")
            return

        # Count by severity
        critical = sum(1 for v in feedback.violations if v.severity.value == "critical")
        major = sum(1 for v in feedback.violations if v.severity.value == "major")
        other = len(feedback.violations) - critical - major

        summary_parts = []
        if critical:
            summary_parts.append(f"[red]{critical} critical[/red]")
        if major:
            summary_parts.append(f"[yellow]{major} major[/yellow]")
        if other:
            summary_parts.append(f"[dim]{other} other[/dim]")

        self.root.add(f"[bold]{len(feedback.violations)} issues:[/bold] {', '.join(summary_parts)}")

        # Show top fix priorities
        if feedback.fix_priority:
            for i, fix in enumerate(feedback.fix_priority[:3], 1):
                self.root.add_leaf(f"  {i}. {fix[:50]}...")
