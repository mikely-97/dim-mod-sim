"""Models for progress tracking."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class AttemptRecord(BaseModel):
    """Record of a single evaluation attempt."""

    timestamp: datetime
    schema_hash: str  # Hash of submitted schema for deduplication
    total_score: int
    max_score: int
    percentage: float
    axis_scores: dict[str, int]
    deduction_count: int


class ScenarioProgress(BaseModel):
    """Progress for a specific (seed, difficulty) combination."""

    seed: int
    difficulty: str
    best_score: int = 0
    best_percentage: float = 0.0
    attempts: list[AttemptRecord] = []
    first_attempt: datetime | None = None
    last_attempt: datetime | None = None

    def record_attempt(
        self,
        total_score: int,
        max_score: int,
        axis_scores: dict[str, int],
        deduction_count: int,
        schema_hash: str,
    ) -> tuple[bool, bool]:
        """Record an attempt and return (is_improvement, is_regression).

        Returns:
            Tuple of (is_improvement, is_regression) compared to previous attempt.
        """
        now = datetime.now()
        percentage = (total_score / max_score * 100) if max_score > 0 else 0

        attempt = AttemptRecord(
            timestamp=now,
            schema_hash=schema_hash,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            axis_scores=axis_scores,
            deduction_count=deduction_count,
        )

        # Track first/last
        if self.first_attempt is None:
            self.first_attempt = now
        self.last_attempt = now

        # Check for improvement/regression vs previous attempt
        is_improvement = False
        is_regression = False

        if self.attempts:
            prev_percentage = self.attempts[-1].percentage
            if percentage > prev_percentage:
                is_improvement = True
            elif percentage < prev_percentage:
                is_regression = True

        # Update best score
        if total_score > self.best_score:
            self.best_score = total_score
            self.best_percentage = percentage

        self.attempts.append(attempt)

        return is_improvement, is_regression

    @property
    def attempt_count(self) -> int:
        """Number of attempts for this scenario."""
        return len(self.attempts)


class ProgressStore(BaseModel):
    """Complete progress store, serializable to JSON."""

    version: str = "1.0"
    scenarios: dict[str, ScenarioProgress] = {}

    @staticmethod
    def _make_key(seed: int, difficulty: str) -> str:
        """Create a key for a scenario."""
        return f"{seed}_{difficulty}"

    def get_scenario(self, seed: int, difficulty: str) -> ScenarioProgress | None:
        """Get progress for a specific scenario."""
        key = self._make_key(seed, difficulty)
        return self.scenarios.get(key)

    def get_or_create_scenario(self, seed: int, difficulty: str) -> ScenarioProgress:
        """Get or create progress for a specific scenario."""
        key = self._make_key(seed, difficulty)
        if key not in self.scenarios:
            self.scenarios[key] = ScenarioProgress(seed=seed, difficulty=difficulty)
        return self.scenarios[key]

    def record_attempt(
        self,
        seed: int,
        difficulty: str,
        total_score: int,
        max_score: int,
        axis_scores: dict[str, int],
        deduction_count: int,
        schema_hash: str,
    ) -> tuple[bool, bool, bool]:
        """Record an evaluation attempt.

        Returns:
            Tuple of (is_improvement, is_regression, is_new_best) for this scenario.
        """
        scenario = self.get_or_create_scenario(seed, difficulty)
        was_best = scenario.best_score

        is_improvement, is_regression = scenario.record_attempt(
            total_score=total_score,
            max_score=max_score,
            axis_scores=axis_scores,
            deduction_count=deduction_count,
            schema_hash=schema_hash,
        )

        is_new_best = total_score > was_best

        return is_improvement, is_regression, is_new_best

    @classmethod
    def load(cls, path: Path) -> ProgressStore:
        """Load progress from file."""
        if not path.exists():
            return cls()

        try:
            with open(path) as f:
                data = json.load(f)
            return cls.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            # Corrupted file, start fresh
            return cls()

    def save(self, path: Path) -> None:
        """Save progress to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, default=str)


def compute_schema_hash(schema_dict: dict[str, Any]) -> str:
    """Compute a hash of a schema for deduplication."""
    # Normalize the schema (sort keys) for consistent hashing
    normalized = json.dumps(schema_dict, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
