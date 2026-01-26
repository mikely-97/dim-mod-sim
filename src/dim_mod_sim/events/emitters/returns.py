"""Return event emitter."""

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.events.emitters.base import EventEmitter
from dim_mod_sim.events.models import (
    BaseEvent,
    EventType,
    LineItem,
    ReturnEvent,
)
from dim_mod_sim.events.state import WorldState
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import ReturnsPricingPolicy, ReturnsReferencePolicy


RETURN_REASONS = [
    "defective",
    "wrong_item",
    "changed_mind",
    "not_as_described",
    "duplicate",
    "too_small",
    "too_large",
    "better_price_elsewhere",
]


class ReturnEventEmitter(EventEmitter):
    """Emits return transaction events."""

    def __init__(self, config: ShopConfiguration, rng: SeededRandom) -> None:
        super().__init__(config, rng)

    def should_emit(self, state: WorldState) -> bool:
        """Returns can happen if there are transactions to return."""
        if not state.transaction_history:
            return False
        # Returns are less frequent than sales
        return self.rng.boolean(0.15)

    def emit(self, state: WorldState) -> list[BaseEvent]:
        """Generate a return event."""
        events: list[BaseEvent] = []

        # Select store
        open_stores = state.get_open_stores()
        if not open_stores:
            return events

        store = self.rng.choice(open_stores)
        register = self.rng.choice(store.registers)
        employee = self.rng.choice(store.employees)

        # Get returnable transactions
        returnable = state.get_returnable_transactions(store.store_id)
        if not returnable:
            return events

        # Determine if we reference original transaction
        original_txn_id: str | None = None
        original_sale = None

        ref_policy = self.config.returns.reference_policy
        if ref_policy == ReturnsReferencePolicy.ALWAYS:
            original_txn_id = self.rng.choice(returnable)
            original_sale = state.transaction_history[original_txn_id]
        elif ref_policy == ReturnsReferencePolicy.SOMETIMES:
            if self.rng.boolean(0.6):
                original_txn_id = self.rng.choice(returnable)
                original_sale = state.transaction_history[original_txn_id]
        # NEVER: original_txn_id stays None

        # Generate return line items
        line_items = self._generate_return_items(state, original_sale, store.store_id)
        if not line_items:
            return events

        # Determine price determination method
        pricing = self.config.returns.pricing_policy
        if pricing == ReturnsPricingPolicy.ORIGINAL_PRICE:
            price_determination = "original"
        elif pricing == ReturnsPricingPolicy.CURRENT_PRICE:
            price_determination = "current"
        else:
            price_determination = "override"

        # Get customer (might be from original transaction)
        customer_id = None
        if original_sale and original_sale.customer_id:
            customer_id = original_sale.customer_id
        else:
            customer_id = state.get_or_create_customer()

        return_event = ReturnEvent(
            event_id=state.generate_event_id(),
            event_type=EventType.RETURN,
            event_timestamp=state.current_timestamp,
            business_effective_date=state.current_business_date,
            return_id=f"RET-{state._event_sequence:08d}",
            store_id=store.store_id,
            register_id=register,
            employee_id=employee,
            customer_id=customer_id,
            original_transaction_id=original_txn_id,
            line_items=tuple(line_items),
            return_reason_code=self.rng.choice(RETURN_REASONS),
            price_determination=price_determination,
        )

        # Update inventory (returns add back)
        for li in line_items:
            state.update_inventory(store.store_id, li.sku, li.quantity)

        events.append(return_event)
        return events

    def _generate_return_items(
        self,
        state: WorldState,
        original_sale: "SaleEvent | None",
        store_id: str,
    ) -> list[LineItem]:
        """Generate line items for a return."""
        line_items: list[LineItem] = []

        if original_sale and not original_sale.is_aggregated:
            # Return some items from the original sale
            num_items = self.rng.integer(1, len(original_sale.line_items))
            items_to_return = self.rng.sample(list(original_sale.line_items), num_items)

            for i, orig_item in enumerate(items_to_return):
                # Might return less than originally purchased
                quantity = self.rng.integer(1, orig_item.quantity)

                # Determine price based on policy
                pricing = self.config.returns.pricing_policy
                if pricing == ReturnsPricingPolicy.ORIGINAL_PRICE:
                    unit_price = orig_item.unit_price_cents
                elif pricing == ReturnsPricingPolicy.CURRENT_PRICE:
                    # Get current price from product
                    product = state.products.get(orig_item.sku)
                    unit_price = product.current_price_cents if product else orig_item.unit_price_cents
                else:
                    # Arbitrary override
                    unit_price = self.rng.integer(
                        orig_item.unit_price_cents // 2,
                        orig_item.unit_price_cents,
                    )

                line_items.append(LineItem(
                    line_number=i + 1,
                    sku=orig_item.sku,
                    quantity=quantity,
                    unit_price_cents=unit_price,
                    discount_cents=0,  # Returns typically don't have discounts
                    promotion_codes=(),
                ))
        else:
            # No original reference or aggregated - generate arbitrary return
            active_products = state.get_active_products()
            if not active_products:
                return line_items

            num_items = self.rng.integer(1, 3)
            for i in range(num_items):
                product = self.rng.choice(active_products)
                quantity = self.rng.integer(1, 3)

                # Price determination
                pricing = self.config.returns.pricing_policy
                if pricing == ReturnsPricingPolicy.ARBITRARY_OVERRIDE:
                    unit_price = self.rng.integer(
                        product.current_price_cents // 2,
                        product.current_price_cents * 2,
                    )
                else:
                    unit_price = product.current_price_cents

                line_items.append(LineItem(
                    line_number=i + 1,
                    sku=product.sku,
                    quantity=quantity,
                    unit_price_cents=unit_price,
                    discount_cents=0,
                    promotion_codes=(),
                ))

        return line_items
