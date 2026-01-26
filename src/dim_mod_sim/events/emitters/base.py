"""Base class for event emitters."""

from abc import ABC, abstractmethod

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.events.models import BaseEvent
from dim_mod_sim.events.state import WorldState
from dim_mod_sim.shop.config import ShopConfiguration


class EventEmitter(ABC):
    """Base class for event emitters."""

    def __init__(self, config: ShopConfiguration, rng: SeededRandom) -> None:
        self.config = config
        self.rng = rng

    @abstractmethod
    def emit(self, state: WorldState) -> list[BaseEvent]:
        """Generate events based on current world state."""
        pass

    @abstractmethod
    def should_emit(self, state: WorldState) -> bool:
        """Determine if this emitter should produce events now."""
        pass
