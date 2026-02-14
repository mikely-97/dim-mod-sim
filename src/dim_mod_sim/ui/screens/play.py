"""Play screen - the main schema editing and evaluation interface."""

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from dim_mod_sim.events.generator import EventGenerator
from dim_mod_sim.evaluator.engine import SchemaEvaluator
from dim_mod_sim.evaluator.feedback import ActionableFeedback
from dim_mod_sim.evaluator.result import EvaluationResult
from dim_mod_sim.progress.tracker import ProgressTracker
from dim_mod_sim.scaffold.generator import ScaffoldGenerator
from dim_mod_sim.schema.parser import parse_schema
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import Difficulty
from dim_mod_sim.ui.widgets.feedback_tree import FeedbackTree
from dim_mod_sim.ui.widgets.schema_editor import SchemaEditor
from dim_mod_sim.ui.widgets.score_display import ScoreDisplay, ScoreSummary


class PlayScreen(Screen):
    """Main play screen with schema editor and feedback panels."""

    CSS = """
    PlayScreen {
        layout: vertical;
    }

    #play-header {
        height: 3;
        padding: 0 2;
        background: $primary-darken-2;
        layout: horizontal;
    }

    #header-info {
        width: 1fr;
    }

    #main-area {
        height: 1fr;
    }

    #editor-panel {
        width: 1fr;
        padding: 1;
    }

    #feedback-panel {
        width: 1fr;
        padding: 1;
    }

    #button-bar {
        height: 5;
        align: center middle;
        padding: 1;
        dock: bottom;
        background: $surface-darken-1;
    }

    #button-bar Button {
        margin: 0 1;
    }

    .panel-title {
        text-style: bold;
        padding-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+e", "evaluate", "Evaluate", show=True),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+l", "load_scaffold", "Load Scaffold", show=True),
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(
        self,
        config: ShopConfiguration,
        difficulty: Difficulty,
        seed: int,
        output_dir: Path,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self.config = config
        self.difficulty = difficulty
        self.seed = seed
        self.output_dir = output_dir

        # Generate events for evaluation
        event_gen = EventGenerator(config, seed)
        self.events = event_gen.generate(num_events=1000, simulation_days=30)

        # Track current evaluation result and schema
        self.current_result: EvaluationResult | None = None
        self.current_schema_dict: dict | None = None

        # Initialize with empty schema
        self.initial_schema = json.dumps(
            {
                "fact_tables": [],
                "dimension_tables": [],
                "relationships": [],
                "bridge_tables": [],
            },
            indent=2,
        )

    def compose(self) -> ComposeResult:
        """Create the play screen layout."""
        yield Header()

        # Play header with scenario info
        with Horizontal(id="play-header"):
            yield Static(
                f"[bold]{self.config.shop_name}[/bold] | "
                f"Seed: {self.seed} | "
                f"Difficulty: {self.difficulty.value.upper()}",
                id="header-info",
            )
            yield ScoreSummary(id="score-summary")

        # Main area with editor and feedback
        with Horizontal(id="main-area"):
            with Vertical(id="editor-panel"):
                yield Static("Schema Editor", classes="panel-title")
                yield SchemaEditor(
                    initial_content=self.initial_schema,
                    id="schema-editor",
                )

            with Vertical(id="feedback-panel"):
                yield Static("Evaluation", classes="panel-title")
                yield ScoreDisplay(id="score-display")
                yield FeedbackTree(id="feedback-tree")

        # Button bar
        with Horizontal(id="button-bar"):
            yield Button("Evaluate", id="btn-evaluate", variant="primary")
            yield Button("Submit Final", id="btn-submit", variant="success")
            yield Button("Load Scaffold", id="btn-scaffold", variant="default")
            yield Button("Save", id="btn-save", variant="default")
            yield Button("Back", id="btn-back", variant="default")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-evaluate":
            self.action_evaluate()
        elif button_id == "btn-submit":
            self.action_submit_final()
        elif button_id == "btn-scaffold":
            self.action_load_scaffold()
        elif button_id == "btn-save":
            self.action_save()
        elif button_id == "btn-back":
            self.action_go_back()

    def action_evaluate(self) -> None:
        """Evaluate the current schema."""
        editor = self.query_one("#schema-editor", SchemaEditor)
        schema_dict = editor.get_parsed_schema()

        if schema_dict is None:
            self.notify("Cannot evaluate: Invalid JSON", severity="error")
            return

        try:
            # Parse schema
            schema = parse_schema(schema_dict)

            # Run evaluation
            evaluator = SchemaEvaluator(self.config, self.events)
            result = evaluator.evaluate(schema)

            # Store result for submission
            self.current_result = result
            self.current_schema_dict = schema_dict

            # Update displays
            score_display = self.query_one("#score-display", ScoreDisplay)
            score_display.result = result

            score_summary = self.query_one("#score-summary", ScoreSummary)
            score_summary.result = result

            # Generate actionable feedback
            feedback = ActionableFeedback.from_result(result)

            feedback_tree = self.query_one("#feedback-tree", FeedbackTree)
            feedback_tree.feedback = feedback

            # Notify with score
            severity = "information" if result.percentage >= 70 else "warning" if result.percentage >= 50 else "error"
            self.notify(
                f"Score: {result.total_score}/{result.max_possible_score} ({result.percentage:.0f}%)",
                title="Evaluation Complete",
                severity=severity,
            )

        except Exception as e:
            self.notify(f"Evaluation failed: {e}", severity="error")

    def action_load_scaffold(self) -> None:
        """Load a generated scaffold into the editor."""
        try:
            generator = ScaffoldGenerator(self.config)
            scaffold = generator.generate()

            # Convert to schema dict format
            schema_dict = scaffold.to_dict()
            schema_json = json.dumps(schema_dict, indent=2)

            # Load into editor
            editor = self.query_one("#schema-editor", SchemaEditor)
            editor.set_content(schema_json)

            self.notify(
                f"Loaded scaffold with {len(scaffold.todos)} TODOs",
                title="Scaffold Loaded",
            )

        except Exception as e:
            self.notify(f"Failed to load scaffold: {e}", severity="error")

    def action_save(self) -> None:
        """Save the current schema to file."""
        editor = self.query_one("#schema-editor", SchemaEditor)
        content = editor.get_content()

        # Save to output directory
        schema_path = self.output_dir / "my_schema.json"
        try:
            with open(schema_path, "w") as f:
                f.write(content)
            self.notify(f"Saved to {schema_path}", title="Schema Saved")
        except Exception as e:
            self.notify(f"Failed to save: {e}", severity="error")

    def action_go_back(self) -> None:
        """Return to scenario screen."""
        self.app.pop_screen()

    def action_submit_final(self) -> None:
        """Submit the final schema and view results."""
        if self.current_result is None:
            self.notify(
                "Please evaluate your schema before submitting",
                severity="warning",
                title="No Evaluation",
            )
            return

        try:
            # Record progress
            tracker = ProgressTracker()
            tracker.record(
                config=self.config,
                difficulty=self.difficulty,
                seed=self.seed,
                result=self.current_result,
                schema_dict=self.current_schema_dict,
            )

            # Navigate to results screen
            from dim_mod_sim.ui.screens.results import ResultsScreen

            results_screen = ResultsScreen(
                result=self.current_result,
                config=self.config,
                difficulty=self.difficulty,
                seed=self.seed,
                output_dir=self.output_dir,
            )
            self.app.push_screen(results_screen)

        except Exception as e:
            self.notify(f"Failed to submit: {e}", severity="error")
