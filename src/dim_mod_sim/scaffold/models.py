"""Scaffold models for schema skeleton generation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScaffoldTodo:
    """A TODO comment for the scaffold indicating a modeling decision."""

    location: str  # e.g., "fact_sales.grain_columns"
    question: str  # The modeling decision question
    hints: list[str] = field(default_factory=list)  # Hints based on shop config
    decision_type: str = "general"  # grain, scd, relationship, measure


@dataclass
class ScaffoldedSchema:
    """A scaffolded schema with intentional gaps and warnings."""

    fact_tables: list[dict[str, Any]] = field(default_factory=list)
    dimension_tables: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    bridge_tables: list[dict[str, Any]] = field(default_factory=list)
    todos: list[ScaffoldTodo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "fact_tables": self.fact_tables,
            "dimension_tables": self.dimension_tables,
            "relationships": self.relationships,
            "bridge_tables": self.bridge_tables,
        }

        # Add todos as comments in the output
        if self.todos:
            result["_scaffold_todos"] = [
                {
                    "location": todo.location,
                    "question": todo.question,
                    "hints": todo.hints,
                    "decision_type": todo.decision_type,
                }
                for todo in self.todos
            ]

        if self.warnings:
            result["_scaffold_warnings"] = self.warnings

        return result
