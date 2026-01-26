"""Sale event emitter."""

from datetime import timedelta

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.events.emitters.base import EventEmitter
from dim_mod_sim.events.models import (
    BaseEvent,
    EventType,
    LineItem,
    Payment,
    SaleEvent,
)
from dim_mod_sim.events.state import WorldState
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import PromotionsPerLineItem, TransactionGrain


PAYMENT_METHODS = ["cash", "credit_card", "debit_card", "gift_card", "mobile_pay"]
RETURN_REASONS = ["defective", "wrong_item", "changed_mind", "not_as_described", "duplicate"]


class SaleEventEmitter(EventEmitter):
    """Emits sale transaction events."""

    def __init__(self, config: ShopConfiguration, rng: SeededRandom) -> None:
        super().__init__(config, rng)

    def should_emit(self, state: WorldState) -> bool:
        """Sales can happen anytime during business hours."""
        hour = state.current_timestamp.hour
        return 8 <= hour <= 22  # Store hours

    def emit(self, state: WorldState) -> list[BaseEvent]:
        """Generate a sale event."""
        events: list[BaseEvent] = []

        # Select store and get employee/register
        open_stores = state.get_open_stores()
        if not open_stores:
            return events

        store = self.rng.choice(open_stores)
        register = self.rng.choice(store.registers)
        employee = self.rng.choice(store.employees)

        # Get or create customer
        customer_id = state.get_or_create_customer()

        # Generate line items
        line_items = self._generate_line_items(state, store.store_id)
        if not line_items:
            return events

        # Generate payments
        total_cents = sum(
            (li.unit_price_cents * li.quantity) - li.discount_cents
            for li in line_items
        )
        payments = self._generate_payments(total_cents)

        # Determine if aggregated (receipt-level grain)
        is_aggregated = False
        if self.config.transactions.grain == TransactionGrain.RECEIPT_LEVEL:
            is_aggregated = True
            line_items = self._aggregate_line_items(line_items, total_cents)
        elif self.config.transactions.grain == TransactionGrain.MIXED:
            is_aggregated = self.rng.boolean(0.3)
            if is_aggregated:
                line_items = self._aggregate_line_items(line_items, total_cents)

        # Determine timestamps
        event_timestamp = state.current_timestamp
        business_date = state.current_business_date

        # Handle different timestamp/business date
        if self.config.time.timestamp_business_date_relation.value == "different":
            # Transaction might be for previous business day (late night)
            if event_timestamp.hour < 4:
                business_date = business_date - timedelta(days=1)

        # Create sale event
        transaction_id = state.generate_transaction_id()
        sale_event = SaleEvent(
            event_id=state.generate_event_id(),
            event_type=EventType.SALE,
            event_timestamp=event_timestamp,
            business_effective_date=business_date,
            transaction_id=transaction_id,
            store_id=store.store_id,
            register_id=register,
            employee_id=employee,
            customer_id=customer_id,
            line_items=tuple(line_items),
            payments=tuple(payments),
            is_aggregated=is_aggregated,
        )

        # Store in history for potential returns
        state.transaction_history[transaction_id] = sale_event

        # Update inventory
        if not is_aggregated:
            for li in line_items:
                state.update_inventory(store.store_id, li.sku, -li.quantity)

        events.append(sale_event)
        return events

    def _generate_line_items(
        self, state: WorldState, store_id: str
    ) -> list[LineItem]:
        """Generate line items for a transaction."""
        line_items: list[LineItem] = []
        active_products = state.get_active_products()

        if not active_products:
            return line_items

        # Decide number of items (1-10)
        num_items = self.rng.integer(1, 10)

        for i in range(num_items):
            product = self.rng.choice(active_products)

            # Handle bundles
            bundle_parent = None
            if product.bundle_components and self.rng.boolean(0.8):
                # Emit bundle as parent + components
                bundle_parent = i + 1

            quantity = self.rng.integer(1, 5)

            # Apply promotions
            promo_codes: list[str] = []
            discount_cents = 0

            applicable_promos = [
                p for p in state.promotions.values()
                if not p.is_basket_level
                and (p.applicable_skus is None or product.sku in p.applicable_skus)
            ]

            if applicable_promos:
                if self.config.promotions.promotions_per_line_item == PromotionsPerLineItem.MANY:
                    # Can have multiple promotions
                    num_promos = self.rng.integer(0, min(3, len(applicable_promos)))
                    selected = self.rng.sample(applicable_promos, num_promos) if num_promos > 0 else []
                else:
                    # At most one promotion
                    selected = [self.rng.choice(applicable_promos)] if self.rng.boolean(0.3) else []

                for promo in selected:
                    promo_codes.append(promo.promotion_code)
                    if promo.discount_type == "percent":
                        discount_cents += (product.current_price_cents * promo.discount_value // 100)
                    elif promo.discount_type == "fixed":
                        discount_cents += promo.discount_value

            # Manual override
            if self.config.transactions.manual_overrides and self.rng.boolean(0.05):
                # Apply arbitrary discount
                discount_cents = self.rng.integer(0, product.current_price_cents // 2)

            line_items.append(LineItem(
                line_number=i + 1,
                sku=product.sku,
                quantity=quantity,
                unit_price_cents=product.current_price_cents,
                discount_cents=discount_cents,
                promotion_codes=tuple(promo_codes),
                bundle_parent_line=bundle_parent,
            ))

        return line_items

    def _aggregate_line_items(
        self, line_items: list[LineItem], total_cents: int
    ) -> list[LineItem]:
        """Aggregate line items for receipt-level grain."""
        # Create a single aggregated line item
        return [LineItem(
            line_number=1,
            sku="AGGREGATE",
            quantity=1,
            unit_price_cents=total_cents,
            discount_cents=0,
            promotion_codes=(),
        )]

    def _generate_payments(self, total_cents: int) -> list[Payment]:
        """Generate payment(s) for a transaction."""
        payments: list[Payment] = []

        if self.config.transactions.multiple_payments and self.rng.boolean(0.2):
            # Split payment
            num_payments = self.rng.integer(2, 3)
            remaining = total_cents

            for i in range(num_payments - 1):
                amount = self.rng.integer(100, remaining - 100)
                payments.append(Payment(
                    payment_method=self.rng.choice(PAYMENT_METHODS),
                    amount_cents=amount,
                    reference_number=f"PAY-{self.rng.integer(100000, 999999)}",
                ))
                remaining -= amount

            payments.append(Payment(
                payment_method=self.rng.choice(PAYMENT_METHODS),
                amount_cents=remaining,
                reference_number=f"PAY-{self.rng.integer(100000, 999999)}",
            ))
        else:
            # Single payment
            payments.append(Payment(
                payment_method=self.rng.choice(PAYMENT_METHODS),
                amount_cents=total_cents,
                reference_number=f"PAY-{self.rng.integer(100000, 999999)}",
            ))

        return payments
