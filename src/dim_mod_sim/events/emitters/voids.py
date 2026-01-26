"""Void and correction event emitters."""

from datetime import timedelta
from typing import Any

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.events.emitters.base import EventEmitter
from dim_mod_sim.events.models import (
    BaseEvent,
    CorrectionEvent,
    EventType,
    VoidEvent,
)
from dim_mod_sim.events.state import WorldState
from dim_mod_sim.shop.config import ShopConfiguration


VOID_REASONS = [
    "customer_request",
    "duplicate_entry",
    "cashier_error",
    "fraud_suspected",
    "test_transaction",
    "system_error",
]

CORRECTION_REASONS = [
    "price_correction",
    "quantity_correction",
    "customer_id_correction",
    "promotion_applied_late",
    "tax_adjustment",
    "data_entry_error",
]

CORRECTABLE_FIELDS = [
    "customer_id",
    "employee_id",
    "line_item_quantity",
    "line_item_price",
    "promotion_code",
]


class VoidEventEmitter(EventEmitter):
    """Emits void events for cancelling transactions."""

    def __init__(self, config: ShopConfiguration, rng: SeededRandom) -> None:
        super().__init__(config, rng)

    def should_emit(self, state: WorldState) -> bool:
        """Check if void events should be emitted."""
        if not self.config.transactions.voids_enabled:
            return False

        # Need transactions to void
        if not state.transaction_history:
            return False

        # Voids are relatively rare
        return self.rng.boolean(0.03)

    def emit(self, state: WorldState) -> list[BaseEvent]:
        """Generate a void event."""
        events: list[BaseEvent] = []

        # Find voidable transactions (not already voided)
        voidable = [
            txn_id for txn_id in state.transaction_history
            if txn_id not in state.voided_events
        ]

        if not voidable:
            return events

        # Select transaction to void
        txn_id = self.rng.choice(voidable)
        original = state.transaction_history[txn_id]

        # Get authorizing manager
        store = state.stores.get(original.store_id)
        authorized_by = self.rng.choice(store.employees) if store else "MGR-UNKNOWN"

        void_event = VoidEvent(
            event_id=state.generate_event_id(),
            event_type=EventType.VOID,
            event_timestamp=state.current_timestamp,
            business_effective_date=state.current_business_date,
            void_id=f"VOID-{state._event_sequence:08d}",
            original_event_id=original.event_id,
            original_event_type=EventType.SALE,
            void_reason=self.rng.choice(VOID_REASONS),
            authorized_by=authorized_by,
        )

        # Mark as voided
        state.voided_events.add(txn_id)

        # Restore inventory
        if not original.is_aggregated:
            for li in original.line_items:
                state.update_inventory(original.store_id, li.sku, li.quantity)

        events.append(void_event)
        return events


class CorrectionEventEmitter(EventEmitter):
    """Emits correction events for backdated fixes."""

    def __init__(self, config: ShopConfiguration, rng: SeededRandom) -> None:
        super().__init__(config, rng)

    def should_emit(self, state: WorldState) -> bool:
        """Check if correction events should be emitted."""
        if not self.config.time.backdated_corrections:
            return False

        # Need transactions to correct
        if not state.transaction_history:
            return False

        # Corrections are relatively rare
        return self.rng.boolean(0.02)

    def emit(self, state: WorldState) -> list[BaseEvent]:
        """Generate a correction event."""
        events: list[BaseEvent] = []

        # Find correctable transactions (not voided)
        correctable = [
            txn_id for txn_id in state.transaction_history
            if txn_id not in state.voided_events
        ]

        if not correctable:
            return events

        # Select transaction to correct
        txn_id = self.rng.choice(correctable)
        original = state.transaction_history[txn_id]

        # Generate corrections
        field_corrections = self._generate_corrections(state, original)

        # The business_effective_date is backdated to when the error occurred
        # but the event_timestamp is now (when we discovered/fixed it)
        backdated_date = original.business_effective_date

        # Optionally adjust the backdate by a few days
        if self.rng.boolean(0.3):
            backdated_date = backdated_date + timedelta(days=self.rng.integer(0, 3))

        correction_event = CorrectionEvent(
            event_id=state.generate_event_id(),
            event_type=EventType.CORRECTION,
            event_timestamp=state.current_timestamp,
            business_effective_date=backdated_date,
            correction_id=f"CORR-{state._event_sequence:08d}",
            original_event_id=original.event_id,
            field_corrections=tuple(field_corrections),
            correction_reason=self.rng.choice(CORRECTION_REASONS),
        )

        events.append(correction_event)
        return events

    def _generate_corrections(
        self, state: WorldState, original: "SaleEvent"
    ) -> list[tuple[str, Any]]:
        """Generate field corrections for an event."""
        corrections: list[tuple[str, Any]] = []

        # Pick 1-2 fields to correct
        num_corrections = self.rng.integer(1, 2)
        fields_to_correct = self.rng.sample(CORRECTABLE_FIELDS, num_corrections)

        for field in fields_to_correct:
            if field == "customer_id":
                # Change customer ID
                new_customer = state.get_or_create_customer()
                corrections.append(("customer_id", new_customer))

            elif field == "employee_id":
                # Change employee ID
                store = state.stores.get(original.store_id)
                if store and store.employees:
                    new_employee = self.rng.choice(store.employees)
                    corrections.append(("employee_id", new_employee))

            elif field == "line_item_quantity":
                # Correct a line item quantity
                if original.line_items and not original.is_aggregated:
                    li = self.rng.choice(original.line_items)
                    new_qty = self.rng.integer(1, li.quantity + 2)
                    corrections.append((
                        f"line_items[{li.line_number}].quantity",
                        new_qty,
                    ))

            elif field == "line_item_price":
                # Correct a line item price
                if original.line_items and not original.is_aggregated:
                    li = self.rng.choice(original.line_items)
                    adjustment = self.rng.integer(-500, 500)
                    new_price = max(1, li.unit_price_cents + adjustment)
                    corrections.append((
                        f"line_items[{li.line_number}].unit_price_cents",
                        new_price,
                    ))

            elif field == "promotion_code":
                # Add a promotion that should have been applied
                applicable_promos = list(state.promotions.keys())
                if applicable_promos:
                    promo = self.rng.choice(applicable_promos)
                    corrections.append(("promotion_code_added", promo))

        return corrections
