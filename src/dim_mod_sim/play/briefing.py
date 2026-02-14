"""Briefing generator for scenario presentation."""

from rich.console import Console
from rich.panel import Panel

from dim_mod_sim.play.framing import (
    ADVERSARIAL_TAGLINES,
    DIFFICULTY_DESCRIPTIONS,
    DifficultyBriefing,
    TrapCategory,
)
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.generator import extract_enabled_traps
from dim_mod_sim.shop.options import Difficulty


class BriefingGenerator:
    """Generates difficulty briefings from shop configurations."""

    def __init__(self, config: ShopConfiguration, difficulty: Difficulty) -> None:
        self.config = config
        self.difficulty = difficulty

    def generate(self) -> DifficultyBriefing:
        """Generate a complete difficulty briefing."""
        traps = extract_enabled_traps(self.config)

        return DifficultyBriefing(
            difficulty_name=self.difficulty.value.upper(),
            difficulty_description=DIFFICULTY_DESCRIPTIONS.get(
                self.difficulty.value,
                "A challenging scenario.",
            ),
            enabled_traps=traps,
            adversarial_tagline=ADVERSARIAL_TAGLINES.get(
                self.difficulty.value,
                "Good luck.",
            ),
        )


def display_briefing(
    briefing: DifficultyBriefing,
    config: ShopConfiguration,
    seed: int,
    num_events: int,
    console: Console,
) -> None:
    """Display the difficulty briefing using Rich console."""
    # Header panel
    console.print()
    console.print(Panel.fit(
        f"[bold]{briefing.difficulty_name} SCENARIO[/bold]\n\n"
        f"Seed: {seed}  |  Shop: {config.shop_name}  |  Events: {num_events:,}",
        border_style="bold",
    ))

    # Adversarial tagline
    console.print()
    console.print(f"[bold italic]{briefing.adversarial_tagline}[/bold italic]")
    console.print()

    # Traps by category
    traps_by_cat = briefing.traps_by_category
    if traps_by_cat:
        trap_lines: list[str] = []

        category_colors = {
            TrapCategory.GRAIN: "red",
            TrapCategory.TEMPORAL: "yellow",
            TrapCategory.IDENTITY: "magenta",
            TrapCategory.SEMANTIC: "cyan",
            TrapCategory.RELATIONSHIP: "blue",
        }

        for category in TrapCategory:
            if category not in traps_by_cat:
                continue

            color = category_colors.get(category, "white")
            trap_lines.append(f"[bold {color}]{category.value.upper()}[/bold {color}]")

            for trap in traps_by_cat[category]:
                trap_lines.append(f"  - {trap.name}")

            trap_lines.append("")

        console.print(Panel(
            "\n".join(trap_lines).strip(),
            title="[bold]Traps Enabled[/bold]",
            border_style="dim",
        ))

    # Threat summary
    if briefing.threat_summary:
        console.print()
        console.print(f"[bold]{config.shop_name}[/bold] will try to break your model by:")
        for threat in briefing.threat_summary:
            console.print(f"  [dim]-[/dim] {threat}")
