"""Seeded random number generator for deterministic generation."""

import random
from typing import Sequence, TypeVar

T = TypeVar("T")


class SeededRandom:
    """Wrapper around random.Random for deterministic generation.

    Provides a consistent interface for random operations that can be
    forked into isolated sub-generators for different components.
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def choice(self, seq: Sequence[T]) -> T:
        """Select a random element from a non-empty sequence."""
        return self._rng.choice(seq)

    def choices(self, seq: Sequence[T], k: int = 1) -> list[T]:
        """Select k random elements with replacement."""
        return self._rng.choices(seq, k=k)

    def weighted_choice(self, options: Sequence[T], weights: Sequence[float]) -> T:
        """Select a random element with weighted probability."""
        return self._rng.choices(options, weights=weights, k=1)[0]

    def boolean(self, true_probability: float = 0.5) -> bool:
        """Return True with the given probability."""
        return self._rng.random() < true_probability

    def integer(self, min_val: int, max_val: int) -> int:
        """Return a random integer in [min_val, max_val]."""
        return self._rng.randint(min_val, max_val)

    def uniform(self, min_val: float, max_val: float) -> float:
        """Return a random float in [min_val, max_val]."""
        return self._rng.uniform(min_val, max_val)

    def sample(self, seq: Sequence[T], k: int) -> list[T]:
        """Return k unique random elements from sequence."""
        return self._rng.sample(list(seq), k)

    def shuffle(self, seq: list[T]) -> None:
        """Shuffle sequence in place."""
        self._rng.shuffle(seq)

    def fork(self, namespace: str) -> "SeededRandom":
        """Create a deterministic child generator for a sub-component.

        The child seed is derived from the parent seed and namespace,
        ensuring that:
        1. Same parent seed + namespace always produces same child
        2. Changes in one namespace don't affect other namespaces
        """
        child_seed = hash((self.seed, namespace)) & 0xFFFFFFFF
        return SeededRandom(child_seed)

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Return a random float from Gaussian distribution."""
        return self._rng.gauss(mu, sigma)

    def triangular(
        self, low: float = 0.0, high: float = 1.0, mode: float | None = None
    ) -> float:
        """Return a random float from triangular distribution."""
        return self._rng.triangular(low, high, mode)
