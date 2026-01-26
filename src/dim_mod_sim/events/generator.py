"""Event generator orchestrator."""

from datetime import timedelta

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.events.emitters.base import EventEmitter
from dim_mod_sim.events.emitters.inventory import InventoryEventEmitter
from dim_mod_sim.events.emitters.returns import ReturnEventEmitter
from dim_mod_sim.events.emitters.sales import SaleEventEmitter
from dim_mod_sim.events.emitters.voids import CorrectionEventEmitter, VoidEventEmitter
from dim_mod_sim.events.models import BaseEvent, EventLog, ProductChangeEvent, EventType
from dim_mod_sim.events.state import WorldState, initialize_world_state
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import ProductHierarchyChangeFrequency, ReturnsReferencePolicy


class EventGenerator:
    """Orchestrates event generation across all emitters."""

    def __init__(self, config: ShopConfiguration, seed: int | None = None) -> None:
        self.config = config
        self.seed = seed if seed is not None else config.seed
        self.rng = SeededRandom(self.seed)
        self.state = initialize_world_state(config, self.rng.fork("world"))
        self.emitters = self._create_emitters()

    def _create_emitters(self) -> list[EventEmitter]:
        """Create emitters based on shop configuration."""
        emitters: list[EventEmitter] = [
            SaleEventEmitter(self.config, self.rng.fork("sales")),
        ]

        # Add return emitter if returns are enabled
        if self.config.returns.reference_policy != ReturnsReferencePolicy.NEVER:
            emitters.append(
                ReturnEventEmitter(self.config, self.rng.fork("returns"))
            )

        # Add void emitter if voids are enabled
        if self.config.transactions.voids_enabled:
            emitters.append(
                VoidEventEmitter(self.config, self.rng.fork("voids"))
            )

        # Add correction emitter if backdated corrections are enabled
        if self.config.time.backdated_corrections:
            emitters.append(
                CorrectionEventEmitter(self.config, self.rng.fork("corrections"))
            )

        # Add inventory emitter if inventory is tracked
        if self.config.inventory.tracked:
            emitters.append(
                InventoryEventEmitter(self.config, self.rng.fork("inventory"))
            )

        return emitters

    def generate(
        self,
        num_events: int = 1000,
        simulation_days: int = 30,
    ) -> EventLog:
        """Generate a complete event log.

        Args:
            num_events: Target number of events to generate
            simulation_days: Maximum days to simulate

        Returns:
            EventLog containing all generated events
        """
        events: list[BaseEvent] = []
        days_simulated = 0

        while len(events) < num_events and days_simulated < simulation_days:
            # Run through a business day
            events.extend(self._simulate_day())
            days_simulated += 1

            # Emit product changes if configured
            if self.config.products.hierarchy_change_frequency != ProductHierarchyChangeFrequency.NONE:
                events.extend(self._maybe_emit_product_changes())

        # Sort by timestamp and trim to requested count
        events.sort(key=lambda e: e.event_timestamp)
        if len(events) > num_events:
            events = events[:num_events]

        return EventLog(
            shop_config_seed=self.config.seed,
            events=events,
        )

    def _simulate_day(self) -> list[BaseEvent]:
        """Simulate a single business day."""
        events: list[BaseEvent] = []

        # Simulate from opening to closing
        business_date = self.state.current_business_date

        while self.state.current_business_date == business_date:
            # Each tick represents some random minutes
            tick_minutes = self.rng.integer(5, 30)

            # Run each emitter
            for emitter in self.emitters:
                if emitter.should_emit(self.state):
                    new_events = emitter.emit(self.state)
                    events.extend(new_events)

            # Advance time
            self.state.advance_time(tick_minutes)

            # Check if day should end (past closing time)
            if self.state.current_timestamp.hour >= 23:
                self.state.advance_business_date()

        return events

    def _maybe_emit_product_changes(self) -> list[BaseEvent]:
        """Possibly emit product hierarchy change events."""
        events: list[BaseEvent] = []

        freq = self.config.products.hierarchy_change_frequency
        if freq == ProductHierarchyChangeFrequency.NONE:
            return events

        # Determine probability based on frequency
        if freq == ProductHierarchyChangeFrequency.OCCASIONAL:
            probability = 0.1
        else:  # FREQUENT
            probability = 0.3

        if not self.rng.boolean(probability):
            return events

        # Select a product to change
        products = list(self.state.products.values())
        if not products:
            return events

        product = self.rng.choice(products)

        # Change hierarchy or price
        change_type = self.rng.choice(["hierarchy", "price"])

        if change_type == "hierarchy":
            # Change category
            old_hierarchy = " > ".join(product.category_hierarchy)
            new_categories = [
                ["Grocery", "Dairy"],
                ["Grocery", "Bakery"],
                ["Electronics", "Audio"],
                ["Clothing", "Men"],
                ["Home", "Kitchen"],
            ]
            new_hierarchy = self.rng.choice(new_categories)
            product.category_hierarchy = new_hierarchy
            new_value = " > ".join(new_hierarchy)

            events.append(ProductChangeEvent(
                event_id=self.state.generate_event_id(),
                event_type=EventType.PRODUCT_CHANGE,
                event_timestamp=self.state.current_timestamp,
                business_effective_date=self.state.current_business_date,
                change_id=f"PCHG-{self.state._event_sequence:08d}",
                sku=product.sku,
                change_type="hierarchy",
                old_value=old_hierarchy,
                new_value=new_value,
            ))
        else:
            # Change price
            old_price = str(product.current_price_cents)
            adjustment = self.rng.integer(-1000, 1000)
            product.current_price_cents = max(100, product.current_price_cents + adjustment)

            events.append(ProductChangeEvent(
                event_id=self.state.generate_event_id(),
                event_type=EventType.PRODUCT_CHANGE,
                event_timestamp=self.state.current_timestamp,
                business_effective_date=self.state.current_business_date,
                change_id=f"PCHG-{self.state._event_sequence:08d}",
                sku=product.sku,
                change_type="price",
                old_value=old_price,
                new_value=str(product.current_price_cents),
            ))

        return events
