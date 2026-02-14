"""Command-line interface for Dim-Mod-Sim."""

import json
import random
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dim_mod_sim.description.generator import DescriptionGenerator
from dim_mod_sim.events.generator import EventGenerator
from dim_mod_sim.evaluator.engine import SchemaEvaluator
from dim_mod_sim.evaluator.feedback import ActionableFeedback, ViolationType
from dim_mod_sim.explain.analyzer import SchemaAnalyzer
from dim_mod_sim.play.session import PlaySession
from dim_mod_sim.scaffold.generator import ScaffoldGenerator
from dim_mod_sim.schema.parser import parse_schema
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.generator import ShopGenerator
from dim_mod_sim.shop.options import Difficulty

app = typer.Typer(
    name="dim-mod-sim",
    help="Dimensional Modeling Simulation Framework",
    no_args_is_help=True,
)
console = Console()


@app.command()
def generate(
    seed: Annotated[
        int | None,
        typer.Option(help="Random seed for deterministic generation"),
    ] = None,
    difficulty: Annotated[
        str,
        typer.Option(help="Difficulty: easy, medium, hard, adversarial"),
    ] = "medium",
    output_dir: Annotated[
        Path,
        typer.Option(help="Output directory"),
    ] = Path("./output"),
    num_events: Annotated[
        int,
        typer.Option(help="Number of events to generate"),
    ] = 1000,
    simulation_days: Annotated[
        int,
        typer.Option(help="Maximum simulation days"),
    ] = 30,
) -> None:
    """Generate a shop configuration, events, and description."""
    # Generate seed if not provided
    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    # Parse difficulty
    try:
        diff = Difficulty(difficulty.lower())
    except ValueError:
        console.print(f"[red]Invalid difficulty: {difficulty}[/red]")
        console.print(f"Valid options: {', '.join(d.value for d in Difficulty)}")
        raise typer.Exit(1)

    console.print(f"[bold]Generating shop with seed {seed}, difficulty {diff.value}[/bold]")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate shop configuration
    with console.status("Generating shop configuration..."):
        shop_gen = ShopGenerator(seed, diff)
        config = shop_gen.generate()

    # Save configuration
    config_path = output_dir / "shop_config.json"
    with open(config_path, "w") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2)
    console.print(f"[green]✓[/green] Shop configuration saved to {config_path}")

    # Generate events
    with console.status(f"Generating {num_events} events..."):
        event_gen = EventGenerator(config, seed)
        events = event_gen.generate(num_events=num_events, simulation_days=simulation_days)

    # Save events
    events_path = output_dir / "events.json"
    with open(events_path, "w") as f:
        json.dump(events.to_dict(), f, indent=2)
    console.print(f"[green]✓[/green] Events saved to {events_path} ({len(events.events)} events)")

    # Generate description
    with console.status("Generating shop description..."):
        desc_gen = DescriptionGenerator(config)
        description = desc_gen.generate()

    # Save description
    desc_path = output_dir / "description.md"
    with open(desc_path, "w") as f:
        f.write(description)
    console.print(f"[green]✓[/green] Description saved to {desc_path}")

    # Print summary
    console.print()
    console.print(Panel.fit(
        f"[bold]{config.shop_name}[/bold]\n\n"
        f"Seed: {seed}\n"
        f"Difficulty: {diff.value}\n"
        f"Events: {len(events.events)}\n"
        f"Output: {output_dir}",
        title="Generation Complete",
    ))


@app.command()
def evaluate(
    shop_config: Annotated[
        Path,
        typer.Argument(help="Path to shop configuration JSON"),
    ],
    events_file: Annotated[
        Path,
        typer.Argument(help="Path to events JSON"),
    ],
    schema_file: Annotated[
        Path,
        typer.Argument(help="Path to submitted schema JSON"),
    ],
    output: Annotated[
        Path | None,
        typer.Option(help="Output path for evaluation report"),
    ] = None,
    format: Annotated[
        str,
        typer.Option(help="Output format: rich, json, markdown, actionable"),
    ] = "actionable",
) -> None:
    """Evaluate a schema submission against a generated shop."""
    # Load shop configuration
    with console.status("Loading shop configuration..."):
        with open(shop_config) as f:
            config_data = json.load(f)
        config = ShopConfiguration.model_validate(config_data)

    # Load events
    with console.status("Loading events..."):
        with open(events_file) as f:
            events_data = json.load(f)
        from dim_mod_sim.events.models import EventLog
        events = EventLog(
            shop_config_seed=events_data["shop_config_seed"],
            events=[],  # We don't need to fully parse events for evaluation
        )

    # Load schema
    with console.status("Loading schema submission..."):
        schema = parse_schema(schema_file)

    # Evaluate
    with console.status("Evaluating schema..."):
        evaluator = SchemaEvaluator(config, events)
        result = evaluator.evaluate(schema)

    # Output results
    if format == "actionable":
        _display_actionable_results(result)
    elif format == "rich":
        _display_rich_results(result)
    elif format == "json":
        output_data = {
            "total_score": result.total_score,
            "max_possible_score": result.max_possible_score,
            "percentage": result.percentage,
            "axis_scores": {
                name: {
                    "score": score.score,
                    "max_score": score.max_score,
                    "percentage": score.percentage,
                    "deductions": [
                        {
                            "points": d.points,
                            "reason": d.reason,
                            "severity": d.severity.value,
                        }
                        for d in score.deductions
                    ],
                }
                for name, score in result.axis_scores.items()
            },
            "critique": result.critique,
            "recommendations": result.recommendations,
        }
        if output:
            with open(output, "w") as f:
                json.dump(output_data, f, indent=2)
            console.print(f"[green]✓[/green] Results saved to {output}")
        else:
            console.print(json.dumps(output_data, indent=2))
    elif format == "markdown":
        report = result.to_report()
        if output:
            with open(output, "w") as f:
                f.write(report)
            console.print(f"[green]✓[/green] Report saved to {output}")
        else:
            console.print(report)


def _display_rich_results(result) -> None:
    """Display evaluation results using Rich."""
    # Overall score
    score_color = "green" if result.percentage >= 70 else "yellow" if result.percentage >= 50 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold {score_color}]{result.total_score}/{result.max_possible_score}[/bold {score_color}] "
        f"({result.percentage:.1f}%)",
        title="Overall Score",
    ))

    # Axis scores table
    table = Table(title="Scores by Axis")
    table.add_column("Axis", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("%", justify="right")
    table.add_column("Issues", justify="right")

    for name, score in result.axis_scores.items():
        pct = score.percentage
        pct_color = "green" if pct >= 70 else "yellow" if pct >= 50 else "red"
        table.add_row(
            name.replace("_", " ").title(),
            str(score.score),
            str(score.max_score),
            f"[{pct_color}]{pct:.0f}%[/{pct_color}]",
            str(len(score.deductions)),
        )

    console.print(table)

    # Critique
    if result.critique:
        console.print()
        console.print(Panel(result.critique, title="Critique"))

    # Recommendations
    if result.recommendations:
        console.print()
        console.print("[bold]Recommendations:[/bold]")
        for i, rec in enumerate(result.recommendations, 1):
            console.print(f"  {i}. {rec}")


def _display_actionable_results(result) -> None:
    """Display actionable evaluation feedback with concrete violations."""
    feedback = ActionableFeedback.from_result(result)

    # Header with score and summary
    score_color = "green" if feedback.percentage >= 70 else "yellow" if feedback.percentage >= 50 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold {score_color}]EVALUATION: {feedback.total_score}/{feedback.max_score} ({feedback.percentage:.1f}%)[/bold {score_color}]\n\n"
        f"{feedback.summary}",
        title="Schema Evaluation",
    ))

    # Group violations by type and display
    violation_labels = {
        ViolationType.GRAIN_VIOLATION: ("GRAIN VIOLATIONS", "red"),
        ViolationType.TEMPORAL_LIE: ("TEMPORAL LIES", "yellow"),
        ViolationType.SEMANTIC_MISMATCH: ("SEMANTIC MISMATCHES", "magenta"),
        ViolationType.DATA_LOSS: ("DATA LOSS RISKS", "red"),
        ViolationType.FAN_OUT_RISK: ("FAN-OUT RISKS", "red"),
        ViolationType.OVER_MODELING: ("OVER-MODELING", "cyan"),
        ViolationType.UNDER_MODELING: ("UNDER-MODELING", "blue"),
    }

    for vtype, violations in feedback.by_category.items():
        if not violations:
            continue

        label, color = violation_labels.get(vtype, (vtype.value.upper(), "white"))

        for v in violations:
            severity_badge = {
                "critical": "[bold red]CRITICAL[/bold red]",
                "major": "[bold yellow]MAJOR[/bold yellow]",
                "moderate": "[yellow]MODERATE[/yellow]",
                "minor": "[dim]MINOR[/dim]",
            }.get(v.severity.value, v.severity.value)

            content = f"{severity_badge} {v.what_went_wrong}\n"

            if v.concrete_example:
                content += f"\n[bold]Example:[/bold]\n{v.concrete_example}\n"

            if v.consequence:
                content += f"\n[bold]Consequence:[/bold]\n{v.consequence}\n"

            if v.fix_hint:
                content += f"\n[bold]Fix:[/bold] {v.fix_hint}"

            if v.affected_tables:
                content += f"\n\n[dim]Affected: {', '.join(v.affected_tables)}[/dim]"

            console.print()
            console.print(Panel(content, title=f"[{color}]{label}[/{color}]", border_style=color))

    # Fix priority
    if feedback.fix_priority:
        console.print()
        priority_content = "\n".join(f"  {i}. {fix}" for i, fix in enumerate(feedback.fix_priority, 1))
        console.print(Panel(priority_content, title="[bold]FIX PRIORITY[/bold]"))


@app.command()
def describe(
    shop_config: Annotated[
        Path,
        typer.Argument(help="Path to shop configuration JSON"),
    ],
    output: Annotated[
        Path | None,
        typer.Option(help="Output path for description"),
    ] = None,
) -> None:
    """Generate a shop description from configuration."""
    # Load configuration
    with console.status("Loading configuration..."):
        with open(shop_config) as f:
            config_data = json.load(f)
        config = ShopConfiguration.model_validate(config_data)

    # Generate description
    with console.status("Generating description..."):
        desc_gen = DescriptionGenerator(config)
        description = desc_gen.generate()

    # Output
    if output:
        with open(output, "w") as f:
            f.write(description)
        console.print(f"[green]✓[/green] Description saved to {output}")
    else:
        console.print(description)


@app.command()
def validate_schema(
    schema_file: Annotated[
        Path,
        typer.Argument(help="Path to schema JSON"),
    ],
) -> None:
    """Validate schema JSON structure without evaluation."""
    try:
        with console.status("Validating schema..."):
            schema = parse_schema(schema_file)

        console.print(f"[green]✓[/green] Schema is valid")
        console.print(f"  Fact tables: {len(schema.fact_tables)}")
        console.print(f"  Dimension tables: {len(schema.dimension_tables)}")
        console.print(f"  Relationships: {len(schema.relationships)}")
        console.print(f"  Bridge tables: {len(schema.bridge_tables)}")

    except Exception as e:
        console.print(f"[red]✗[/red] Schema validation failed: {e}")
        raise typer.Exit(1)


@app.command()
def info(
    shop_config: Annotated[
        Path,
        typer.Argument(help="Path to shop configuration JSON"),
    ],
) -> None:
    """Display information about a shop configuration."""
    # Load configuration
    with open(shop_config) as f:
        config_data = json.load(f)
    config = ShopConfiguration.model_validate(config_data)

    # Display info
    console.print(Panel.fit(f"[bold]{config.shop_name}[/bold]", title="Shop Info"))

    table = Table(show_header=False)
    table.add_column("Category", style="cyan")
    table.add_column("Setting")
    table.add_column("Value")

    # Transaction settings
    table.add_row("Transactions", "Grain", config.transactions.grain.value)
    table.add_row("", "Multiple payments", str(config.transactions.multiple_payments))
    table.add_row("", "Voids enabled", str(config.transactions.voids_enabled))
    table.add_row("", "Manual overrides", str(config.transactions.manual_overrides))

    # Time settings
    table.add_row("Time", "Timestamp/business date", config.time.timestamp_business_date_relation.value)
    table.add_row("", "Late-arriving events", str(config.time.late_arriving_events))
    table.add_row("", "Backdated corrections", str(config.time.backdated_corrections))

    # Product settings
    table.add_row("Products", "SKU reuse", str(config.products.sku_reuse))
    table.add_row("", "Hierarchy changes", config.products.hierarchy_change_frequency.value)
    table.add_row("", "Bundled products", str(config.products.bundled_products))
    table.add_row("", "Virtual products", str(config.products.virtual_products))

    # Customer settings
    table.add_row("Customers", "Anonymous allowed", str(config.customers.anonymous_allowed))
    table.add_row("", "ID reliability", config.customers.customer_id_reliability.value)
    table.add_row("", "Household grouping", str(config.customers.household_grouping))

    # Store settings
    table.add_row("Stores", "Physical stores", str(config.stores.physical_stores))
    table.add_row("", "Online channel", str(config.stores.online_channel))
    table.add_row("", "Cross-store returns", str(config.stores.cross_store_returns))
    table.add_row("", "Store lifecycle", str(config.stores.store_lifecycle_changes))

    # Promotion settings
    table.add_row("Promotions", "Per line item", config.promotions.promotions_per_line_item.value)
    table.add_row("", "Stackable", str(config.promotions.stackable_promotions))
    table.add_row("", "Basket-level", str(config.promotions.basket_level_promotions))
    table.add_row("", "Post-transaction", str(config.promotions.post_transaction_promotions))

    # Returns settings
    table.add_row("Returns", "Reference policy", config.returns.reference_policy.value)
    table.add_row("", "Pricing policy", config.returns.pricing_policy.value)

    # Inventory settings
    table.add_row("Inventory", "Tracked", str(config.inventory.tracked))
    if config.inventory.inventory_type:
        table.add_row("", "Type", config.inventory.inventory_type.value)

    console.print(table)


@app.command()
def scaffold(
    shop_config: Annotated[
        Path,
        typer.Argument(help="Path to shop configuration JSON"),
    ],
    output: Annotated[
        Path | None,
        typer.Option(help="Output path for scaffold JSON"),
    ] = None,
) -> None:
    """Generate a schema scaffold from shop configuration.

    Creates a skeleton schema with TODOs and warnings, NOT a correct solution.
    Use this to eliminate blank-file paralysis, not thinking.
    """
    # Load configuration
    with console.status("Loading configuration..."):
        with open(shop_config) as f:
            config_data = json.load(f)
        config = ShopConfiguration.model_validate(config_data)

    # Generate scaffold
    with console.status("Generating scaffold..."):
        generator = ScaffoldGenerator(config)
        scaffolded = generator.generate()

    # Output
    scaffold_dict = scaffolded.to_dict()

    if output:
        with open(output, "w") as f:
            json.dump(scaffold_dict, f, indent=2)
        console.print(f"[green]✓[/green] Scaffold saved to {output}")
    else:
        console.print(json.dumps(scaffold_dict, indent=2))

    # Show summary
    console.print()
    console.print(Panel.fit(
        f"[bold]Scaffold Summary[/bold]\n\n"
        f"Fact tables: {len(scaffolded.fact_tables)}\n"
        f"Dimension tables: {len(scaffolded.dimension_tables)}\n"
        f"Relationships: {len(scaffolded.relationships)}\n"
        f"TODOs: {len(scaffolded.todos)}\n"
        f"Warnings: {len(scaffolded.warnings)}",
        title="Generated",
        border_style="yellow",
    ))

    if scaffolded.todos:
        console.print()
        console.print("[bold yellow]Key decisions needed:[/bold yellow]")
        for todo in scaffolded.todos[:5]:
            console.print(f"  [dim]•[/dim] {todo.question}")

    if scaffolded.warnings:
        console.print()
        console.print("[bold red]Warnings:[/bold red]")
        for warning in scaffolded.warnings:
            console.print(f"  [dim]![/dim] {warning}")


@app.command()
def play(
    seed: Annotated[
        int | None,
        typer.Option(help="Random seed (auto-generated if not provided)"),
    ] = None,
    difficulty: Annotated[
        str,
        typer.Option(help="Difficulty: easy, medium, hard, adversarial"),
    ] = "medium",
    output_dir: Annotated[
        Path,
        typer.Option(help="Output directory"),
    ] = Path("./output"),
    num_events: Annotated[
        int,
        typer.Option(help="Number of events to generate"),
    ] = 1000,
    scaffold: Annotated[
        bool,
        typer.Option(help="Generate schema scaffold"),
    ] = True,
) -> None:
    """Start an interactive modeling challenge.

    This is the primary entry point for Dim-Mod-Sim. It orchestrates:
    - Scenario generation
    - Difficulty briefing with trap warnings
    - Schema scaffold creation
    - Interactive evaluation loop
    """
    # Generate seed if not provided
    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    # Parse difficulty
    try:
        diff = Difficulty(difficulty.lower())
    except ValueError:
        console.print(f"[red]Invalid difficulty: {difficulty}[/red]")
        console.print(f"Valid options: {', '.join(d.value for d in Difficulty)}")
        raise typer.Exit(1)

    # Run the play session
    session = PlaySession(
        seed=seed,
        difficulty=diff,
        output_dir=output_dir,
        num_events=num_events,
        enable_scaffold=scaffold,
        console=console,
    )

    try:
        session.run()
    except KeyboardInterrupt:
        console.print("\n[dim]Session interrupted.[/dim]")
        raise typer.Exit(0)


@app.command()
def explain(
    shop_config: Annotated[
        Path,
        typer.Argument(help="Path to shop configuration JSON"),
    ],
    events_file: Annotated[
        Path,
        typer.Argument(help="Path to events JSON"),
    ],
    schema_file: Annotated[
        Path,
        typer.Argument(help="Path to submitted schema JSON"),
    ],
    verbose: Annotated[
        bool,
        typer.Option(help="Show detailed event traces"),
    ] = False,
) -> None:
    """Show concrete examples where your schema produces wrong answers.

    This diagnostic command analyzes your schema against the shop configuration
    and shows specific scenarios where queries would return incorrect results.
    """
    # Load shop configuration
    with console.status("Loading shop configuration..."):
        with open(shop_config) as f:
            config_data = json.load(f)
        config = ShopConfiguration.model_validate(config_data)

    # Load events
    with console.status("Loading events..."):
        with open(events_file) as f:
            events_data = json.load(f)
        from dim_mod_sim.events.models import EventLog
        events = EventLog(
            shop_config_seed=events_data["shop_config_seed"],
            events=[],
        )

    # Load schema
    with console.status("Loading schema..."):
        schema = parse_schema(schema_file)

    # Analyze
    with console.status("Analyzing schema..."):
        analyzer = SchemaAnalyzer(config, events)
        result = analyzer.analyze(schema)

    # Display results
    console.print()
    console.print(Panel.fit(
        f"[bold]SCHEMA EXPLANATION[/bold]\n\n{result.summary}",
        title="Diagnostic Analysis",
    ))

    if not result.has_issues():
        console.print()
        console.print("[green]No specific failure scenarios identified.[/green]")
        console.print("[dim]This doesn't mean the schema is perfect - just that[/dim]")
        console.print("[dim]no concrete failing cases were generated.[/dim]")
        return

    # Display each scenario
    severity_colors = {
        "critical": "red",
        "major": "yellow",
        "moderate": "cyan",
        "minor": "dim",
    }

    for i, scenario in enumerate(result.query_scenarios, 1):
        color = severity_colors.get(scenario.severity, "white")

        content = f"[bold]Business Question:[/bold]\n{scenario.business_question}\n\n"
        content += f"[bold]What Actually Happened:[/bold]\n{scenario.setup_description}\n\n"
        content += f"[bold green]Expected Answer:[/bold green] {scenario.expected_answer}\n"
        content += f"[bold red]Your Model Returns:[/bold red] {scenario.actual_with_schema}\n\n"
        content += f"[bold]Why It's Wrong:[/bold]\n{scenario.why_wrong}\n\n"
        content += f"[dim]Root Cause: {scenario.root_cause}[/dim]"

        if verbose and scenario.events_involved:
            content += f"\n\n[dim]Events: {', '.join(scenario.events_involved)}[/dim]"

        console.print()
        console.print(Panel(
            content,
            title=f"[{color}]Scenario {i}: {scenario.scenario_name}[/{color}]",
            border_style=color,
        ))


@app.command()
def ui(
    web: Annotated[
        bool,
        typer.Option("--web", "-w", help="Serve as web app instead of TUI"),
    ] = False,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Web server port (only with --web)"),
    ] = 8080,
) -> None:
    """Launch the interactive TUI (or web interface with --web).

    The TUI provides a visual interface for:
    - Starting new modeling challenges
    - Editing schemas with live feedback
    - Tracking progress across attempts
    - Viewing detailed violation explanations
    """
    from dim_mod_sim.ui.app import DimModSimApp

    if web:
        try:
            from textual_web import run_app
            console.print(f"[bold]Starting web server on port {port}...[/bold]")
            console.print(f"Open http://localhost:{port} in your browser")
            run_app(DimModSimApp, port=port)
        except ImportError:
            console.print("[red]textual-web is not installed.[/red]")
            console.print("Install it with: pip install textual-web")
            console.print("Or: poetry install --extras web")
            raise typer.Exit(1)
    else:
        tui_app = DimModSimApp()
        tui_app.run()


if __name__ == "__main__":
    app()
