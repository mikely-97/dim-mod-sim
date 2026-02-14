"""Play session orchestrator for interactive challenges."""

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from dim_mod_sim.description.generator import DescriptionGenerator
from dim_mod_sim.events.generator import EventGenerator
from dim_mod_sim.evaluator.engine import SchemaEvaluator
from dim_mod_sim.evaluator.feedback import ActionableFeedback, ViolationType
from dim_mod_sim.play.briefing import BriefingGenerator, display_briefing
from dim_mod_sim.progress.tracker import ProgressTracker
from dim_mod_sim.scaffold.generator import ScaffoldGenerator
from dim_mod_sim.schema.parser import parse_schema
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.generator import ShopGenerator
from dim_mod_sim.shop.options import Difficulty


class PlaySession:
    """Orchestrates an interactive play session."""

    def __init__(
        self,
        seed: int,
        difficulty: Difficulty,
        output_dir: Path,
        num_events: int = 1000,
        simulation_days: int = 30,
        enable_scaffold: bool = True,
        console: Console | None = None,
    ) -> None:
        self.seed = seed
        self.difficulty = difficulty
        self.output_dir = output_dir
        self.num_events = num_events
        self.simulation_days = simulation_days
        self.enable_scaffold = enable_scaffold
        self.console = console or Console()

        # Progress tracking
        self.progress_tracker = ProgressTracker()

        # Generated artifacts
        self.config: ShopConfiguration | None = None
        self.events = None
        self.evaluator: SchemaEvaluator | None = None

    def run(self) -> None:
        """Run the complete play session."""
        self._generate_scenario()
        self._show_briefing()
        self._offer_description()

        if self.enable_scaffold:
            self._generate_scaffold()

        self._evaluation_loop()
        self._show_session_summary()

    def _generate_scenario(self) -> None:
        """Generate the shop configuration and events."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate shop configuration
        with self.console.status("[bold]Generating shop configuration...[/bold]"):
            shop_gen = ShopGenerator(self.seed, self.difficulty)
            self.config = shop_gen.generate()

        # Save configuration
        config_path = self.output_dir / "shop_config.json"
        with open(config_path, "w") as f:
            json.dump(self.config.model_dump(mode="json"), f, indent=2)

        # Generate events
        with self.console.status(f"[bold]Generating {self.num_events:,} events...[/bold]"):
            event_gen = EventGenerator(self.config, self.seed)
            self.events = event_gen.generate(
                num_events=self.num_events,
                simulation_days=self.simulation_days,
            )

        # Save events
        events_path = self.output_dir / "events.json"
        with open(events_path, "w") as f:
            json.dump(self.events.to_dict(), f, indent=2)

        # Initialize evaluator
        self.evaluator = SchemaEvaluator(self.config, self.events)

        self.console.print(f"[green]✓[/green] Scenario generated in {self.output_dir}")

    def _show_briefing(self) -> None:
        """Display the difficulty briefing."""
        if self.config is None:
            return

        briefing_gen = BriefingGenerator(self.config, self.difficulty)
        briefing = briefing_gen.generate()

        display_briefing(
            briefing,
            self.config,
            self.seed,
            len(self.events.events) if self.events else self.num_events,
            self.console,
        )

    def _offer_description(self) -> None:
        """Offer to show the full business description."""
        if self.config is None:
            return

        self.console.print()
        if Confirm.ask("Show full business description?", default=False):
            desc_gen = DescriptionGenerator(self.config)
            description = desc_gen.generate()

            # Save description
            desc_path = self.output_dir / "description.md"
            with open(desc_path, "w") as f:
                f.write(description)

            self.console.print()
            self.console.print(Panel(description, title="Business Description"))
            self.console.print(f"\n[dim]Saved to {desc_path}[/dim]")

    def _generate_scaffold(self) -> None:
        """Generate and save the schema scaffold."""
        if self.config is None:
            return

        with self.console.status("[bold]Generating schema scaffold...[/bold]"):
            scaffold_gen = ScaffoldGenerator(self.config)
            scaffold = scaffold_gen.generate()

        scaffold_path = self.output_dir / "scaffold.json"
        with open(scaffold_path, "w") as f:
            json.dump(scaffold.to_dict(), f, indent=2)

        self.console.print()
        self.console.print(Panel.fit(
            f"Schema scaffold saved to [bold]{scaffold_path}[/bold]\n\n"
            f"[dim]This is a starting point with TODOs, not a correct solution.[/dim]\n"
            f"[dim]Copy it, rename it, and fill in the modeling decisions.[/dim]",
            title="[yellow]Scaffold Ready[/yellow]",
            border_style="yellow",
        ))

    def _evaluation_loop(self) -> None:
        """Run the evaluation loop until user exits."""
        if self.evaluator is None:
            return

        attempt = 0

        self.console.print()
        self.console.print("[bold]Ready for evaluation.[/bold]")
        self.console.print("[dim]Enter the path to your schema JSON, or 'quit' to exit.[/dim]")

        while True:
            self.console.print()
            schema_path = Prompt.ask(
                "[bold]Schema path[/bold]",
                default="quit",
            )

            if schema_path.lower() in ("quit", "q", "exit", "done"):
                break

            path = Path(schema_path)
            if not path.exists():
                self.console.print(f"[red]File not found: {path}[/red]")
                continue

            try:
                attempt += 1
                self._evaluate_schema(path, attempt)
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

            if not Confirm.ask("Try another schema?", default=True):
                break

    def _evaluate_schema(self, schema_path: Path, attempt: int) -> None:
        """Evaluate a schema and display results."""
        if self.evaluator is None:
            return

        with self.console.status("[bold]Evaluating schema...[/bold]"):
            schema = parse_schema(schema_path)
            result = self.evaluator.evaluate(schema)

            # Load schema dict for progress tracking
            with open(schema_path) as f:
                schema_dict = json.load(f)

        feedback = ActionableFeedback.from_result(result)

        # Record progress
        is_improvement, is_regression, is_new_best = self.progress_tracker.record_attempt(
            seed=self.seed,
            difficulty=self.difficulty.value,
            result=result,
            schema_dict=schema_dict,
        )

        # Header with score
        score_color = (
            "green" if feedback.percentage >= 70
            else "yellow" if feedback.percentage >= 50
            else "red"
        )

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold {score_color}]ATTEMPT #{attempt}: "
            f"{feedback.total_score}/{feedback.max_score} ({feedback.percentage:.1f}%)"
            f"[/bold {score_color}]\n\n"
            f"{feedback.summary}",
            title="Evaluation Result",
        ))

        # Show improvement/regression
        self.progress_tracker.display_improvement(
            is_improvement, is_regression, is_new_best, self.console
        )

        # Show violations by category
        self._display_violations(feedback)

        # Show fix priority
        if feedback.fix_priority:
            self.console.print()
            priority_content = "\n".join(
                f"  {i}. {fix}" for i, fix in enumerate(feedback.fix_priority, 1)
            )
            self.console.print(Panel(priority_content, title="[bold]Fix Priority[/bold]"))

    def _display_violations(self, feedback: ActionableFeedback) -> None:
        """Display violations grouped by category."""
        violation_labels = {
            ViolationType.GRAIN_VIOLATION: ("GRAIN VIOLATIONS", "red"),
            ViolationType.TEMPORAL_LIE: ("TEMPORAL LIES", "yellow"),
            ViolationType.SEMANTIC_MISMATCH: ("SEMANTIC MISMATCHES", "magenta"),
            ViolationType.DATA_LOSS: ("DATA LOSS RISKS", "red"),
            ViolationType.FAN_OUT_RISK: ("FAN-OUT RISKS", "red"),
            ViolationType.OVER_MODELING: ("OVER-MODELING", "cyan"),
            ViolationType.UNDER_MODELING: ("UNDER-MODELING", "blue"),
        }

        # Show top violations (limit to avoid overwhelming output)
        shown = 0
        max_to_show = 5

        for v in feedback.violations:
            if shown >= max_to_show:
                remaining = len(feedback.violations) - shown
                if remaining > 0:
                    self.console.print(f"\n[dim]...and {remaining} more issues[/dim]")
                break

            label, color = violation_labels.get(
                v.violation_type,
                (v.violation_type.value.upper(), "white"),
            )

            severity_badge = {
                "critical": "[bold red]CRITICAL[/bold red]",
                "major": "[bold yellow]MAJOR[/bold yellow]",
                "moderate": "[yellow]MODERATE[/yellow]",
                "minor": "[dim]MINOR[/dim]",
            }.get(v.severity.value, v.severity.value)

            content = f"{severity_badge} {v.what_went_wrong}"

            if v.consequence:
                content += f"\n[dim]→ {v.consequence}[/dim]"

            if v.fix_hint:
                content += f"\n[bold]Fix:[/bold] {v.fix_hint}"

            self.console.print()
            self.console.print(Panel(
                content,
                title=f"[{color}]{label}[/{color}]",
                border_style=color,
            ))
            shown += 1

    def _show_session_summary(self) -> None:
        """Show summary when session ends."""
        # Show progress for this scenario
        self.console.print()
        self.progress_tracker.display_progress(
            self.seed, self.difficulty.value, self.console
        )

        self.console.print()
        self.console.print(Panel.fit(
            f"[bold]Session Complete[/bold]\n\n"
            f"Seed: {self.seed}\n"
            f"Difficulty: {self.difficulty.value}\n"
            f"Output: {self.output_dir}",
            border_style="dim",
        ))
