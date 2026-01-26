"""Inventory event emitter."""

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.events.emitters.base import EventEmitter
from dim_mod_sim.events.models import (
    BaseEvent,
    EventType,
    InventoryAdjustmentEvent,
    InventorySnapshotEvent,
)
from dim_mod_sim.events.state import WorldState
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import InventoryType


ADJUSTMENT_REASONS = [
    "receiving",
    "damage",
    "theft",
    "count_correction",
    "transfer_in",
    "transfer_out",
    "expired",
    "return_to_vendor",
]


class InventoryEventEmitter(EventEmitter):
    """Emits inventory adjustment and snapshot events."""

    def __init__(self, config: ShopConfiguration, rng: SeededRandom) -> None:
        super().__init__(config, rng)
        self._last_snapshot_date = None

    def should_emit(self, state: WorldState) -> bool:
        """Check if inventory events should be emitted."""
        if not self.config.inventory.tracked:
            return False

        inv_type = self.config.inventory.inventory_type

        # For transactional, emit adjustments periodically
        if inv_type in (InventoryType.TRANSACTIONAL, InventoryType.BOTH):
            if self.rng.boolean(0.05):  # 5% chance per tick
                return True

        # For snapshots, emit at end of day
        if inv_type in (InventoryType.PERIODIC_SNAPSHOT, InventoryType.BOTH):
            if (
                self._last_snapshot_date != state.current_business_date
                and state.current_timestamp.hour >= 22
            ):
                return True

        return False

    def emit(self, state: WorldState) -> list[BaseEvent]:
        """Generate inventory events."""
        events: list[BaseEvent] = []

        if not self.config.inventory.tracked:
            return events

        inv_type = self.config.inventory.inventory_type

        # Check if we should do a snapshot
        should_snapshot = (
            inv_type in (InventoryType.PERIODIC_SNAPSHOT, InventoryType.BOTH)
            and self._last_snapshot_date != state.current_business_date
            and state.current_timestamp.hour >= 22
        )

        if should_snapshot:
            events.extend(self._emit_snapshots(state))
            self._last_snapshot_date = state.current_business_date
        elif inv_type in (InventoryType.TRANSACTIONAL, InventoryType.BOTH):
            events.extend(self._emit_adjustment(state))

        return events

    def _emit_adjustment(self, state: WorldState) -> list[BaseEvent]:
        """Emit an inventory adjustment event."""
        events: list[BaseEvent] = []

        open_stores = state.get_open_stores()
        if not open_stores:
            return events

        store = self.rng.choice(open_stores)
        active_products = state.get_active_products()
        if not active_products:
            return events

        product = self.rng.choice(active_products)
        reason = self.rng.choice(ADJUSTMENT_REASONS)

        # Determine quantity change based on reason
        if reason in ("receiving", "transfer_in", "count_correction"):
            quantity_change = self.rng.integer(1, 50)
        elif reason in ("damage", "theft", "expired", "return_to_vendor", "transfer_out"):
            quantity_change = -self.rng.integer(1, 10)
        else:
            quantity_change = self.rng.integer(-10, 10)

        # Update state
        state.update_inventory(store.store_id, product.sku, quantity_change)

        events.append(InventoryAdjustmentEvent(
            event_id=state.generate_event_id(),
            event_type=EventType.INVENTORY_ADJUSTMENT,
            event_timestamp=state.current_timestamp,
            business_effective_date=state.current_business_date,
            adjustment_id=f"ADJ-{state._event_sequence:08d}",
            store_id=store.store_id,
            sku=product.sku,
            quantity_change=quantity_change,
            reason_code=reason,
            reference_event_id=None,
        ))

        return events

    def _emit_snapshots(self, state: WorldState) -> list[BaseEvent]:
        """Emit inventory snapshots for all store/SKU combinations."""
        events: list[BaseEvent] = []

        snapshot_type = "daily"

        for store_id, store_inv in state.inventory.items():
            for sku, quantity in store_inv.items():
                events.append(InventorySnapshotEvent(
                    event_id=state.generate_event_id(),
                    event_type=EventType.INVENTORY_SNAPSHOT,
                    event_timestamp=state.current_timestamp,
                    business_effective_date=state.current_business_date,
                    snapshot_id=f"SNAP-{state._event_sequence:08d}",
                    store_id=store_id,
                    sku=sku,
                    quantity_on_hand=quantity,
                    snapshot_type=snapshot_type,
                ))

        return events
