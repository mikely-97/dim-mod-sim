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
        typer.Option(help="Output format: rich, json, markdown"),
    ] = "rich",
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
    if format == "rich":
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


if __name__ == "__main__":
    app()
