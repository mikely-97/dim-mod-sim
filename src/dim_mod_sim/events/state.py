"""World state for event simulation."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import CustomerIdReliability


@dataclass
class ProductState:
    """State of a product in the simulation."""

    sku: str
    name: str
    category_hierarchy: list[str]
    current_price_cents: int
    is_active: bool = True
    is_virtual: bool = False
    bundle_components: list[str] | None = None


@dataclass
class StoreState:
    """State of a store in the simulation."""

    store_id: str
    store_name: str
    channel: str  # "physical", "online"
    is_open: bool = True
    open_date: date | None = None
    close_date: date | None = None
    registers: list[str] = field(default_factory=list)
    employees: list[str] = field(default_factory=list)


@dataclass
class CustomerState:
    """State of a customer in the simulation."""

    customer_id: str
    household_id: str | None = None
    is_anonymous: bool = False


@dataclass
class PromotionState:
    """State of a promotion in the simulation."""

    promotion_code: str
    promotion_name: str
    discount_type: str  # "percent", "fixed", "bogo"
    discount_value: int  # Percent (0-100) or cents
    applicable_skus: list[str] | None = None  # None = all products
    start_date: date | None = None
    end_date: date | None = None
    is_basket_level: bool = False
    is_stackable: bool = False


@dataclass
class WorldState:
    """Tracks the simulated world state during event generation."""

    config: ShopConfiguration
    rng: SeededRandom

    # Current time in simulation
    current_timestamp: datetime = field(default_factory=lambda: datetime(2024, 1, 1, 9, 0, 0))
    current_business_date: date = field(default_factory=lambda: date(2024, 1, 1))

    # Master data
    products: dict[str, ProductState] = field(default_factory=dict)
    stores: dict[str, StoreState] = field(default_factory=dict)
    customers: dict[str, CustomerState] = field(default_factory=dict)
    promotions: dict[str, PromotionState] = field(default_factory=dict)

    # Inventory tracking: store_id -> sku -> quantity
    inventory: dict[str, dict[str, int]] = field(default_factory=dict)

    # Transaction history for returns referencing, corrections, etc.
    transaction_history: dict[str, "SaleEvent"] = field(default_factory=dict)
    voided_events: set[str] = field(default_factory=set)

    # Event sequence for event_id generation
    _event_sequence: int = 0
    _transaction_sequence: int = 0

    def generate_event_id(self) -> str:
        """Generate a unique event ID."""
        self._event_sequence += 1
        return f"EVT-{self._event_sequence:08d}"

    def generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        self._transaction_sequence += 1
        return f"TXN-{self._transaction_sequence:08d}"

    def advance_time(self, minutes: int) -> None:
        """Advance simulation time by the specified minutes."""
        self.current_timestamp += timedelta(minutes=minutes)

    def advance_business_date(self) -> None:
        """Move to next business date and reset to morning."""
        self.current_business_date += timedelta(days=1)
        # Reset time to morning of new business day
        self.current_timestamp = datetime.combine(
            self.current_business_date,
            datetime.min.time().replace(hour=9),
        )

    def get_open_stores(self) -> list[StoreState]:
        """Get all currently open stores."""
        return [s for s in self.stores.values() if s.is_open]

    def get_active_products(self) -> list[ProductState]:
        """Get all currently active products."""
        return [p for p in self.products.values() if p.is_active]

    def get_returnable_transactions(self, store_id: str | None = None) -> list[str]:
        """Get transaction IDs that can be returned.

        Args:
            store_id: If cross-store returns disabled, filter by store
        """
        returnable = []
        for txn_id, event in self.transaction_history.items():
            # Skip voided transactions
            if txn_id in self.voided_events:
                continue
            # If cross-store returns disabled, must match store
            if store_id and not self.config.stores.cross_store_returns:
                if event.store_id != store_id:
                    continue
            returnable.append(txn_id)
        return returnable

    def get_or_create_customer(self) -> str | None:
        """Get a customer ID based on configuration."""
        reliability = self.config.customers.customer_id_reliability

        if reliability == CustomerIdReliability.ABSENT:
            return None

        # Check if anonymous purchase
        if self.config.customers.anonymous_allowed and self.rng.boolean(0.3):
            return None

        # For unreliable IDs, sometimes create duplicates
        if reliability == CustomerIdReliability.UNRELIABLE and self.rng.boolean(0.2):
            # Create a new customer ID even if might be same person
            pass

        # Return existing customer or create new
        if self.customers and self.rng.boolean(0.7):
            return self.rng.choice(list(self.customers.keys()))

        # Create new customer
        customer_id = f"CUST-{len(self.customers) + 1:06d}"
        household_id = None
        if self.config.customers.household_grouping and self.rng.boolean(0.4):
            # Join existing household or create new
            existing_households = {
                c.household_id for c in self.customers.values() if c.household_id
            }
            if existing_households and self.rng.boolean(0.5):
                household_id = self.rng.choice(list(existing_households))
            else:
                household_id = f"HH-{len(existing_households) + 1:04d}"

        self.customers[customer_id] = CustomerState(
            customer_id=customer_id,
            household_id=household_id,
        )
        return customer_id

    def update_inventory(self, store_id: str, sku: str, quantity_change: int) -> None:
        """Update inventory for a store/SKU combination."""
        if not self.config.inventory.tracked:
            return

        if store_id not in self.inventory:
            self.inventory[store_id] = {}

        if sku not in self.inventory[store_id]:
            self.inventory[store_id][sku] = 100  # Default starting inventory

        self.inventory[store_id][sku] += quantity_change

    def get_inventory(self, store_id: str, sku: str) -> int:
        """Get current inventory level."""
        return self.inventory.get(store_id, {}).get(sku, 0)


def initialize_world_state(
    config: ShopConfiguration,
    rng: SeededRandom,
    num_products: int = 50,
    num_stores: int = 5,
    num_promotions: int = 10,
) -> WorldState:
    """Create initial world state with master data."""
    state = WorldState(config=config, rng=rng)

    # Generate products
    product_rng = rng.fork("products")
    categories = [
        ["Grocery", "Dairy"],
        ["Grocery", "Bakery"],
        ["Grocery", "Produce"],
        ["Electronics", "Audio"],
        ["Electronics", "Computing"],
        ["Clothing", "Men"],
        ["Clothing", "Women"],
        ["Home", "Kitchen"],
        ["Home", "Garden"],
    ]

    for i in range(num_products):
        sku = f"SKU-{i + 1:05d}"
        category = product_rng.choice(categories)
        is_virtual = config.products.virtual_products and product_rng.boolean(0.1)
        is_bundle = config.products.bundled_products and product_rng.boolean(0.05)

        bundle_components = None
        if is_bundle and i > 2:
            # Bundle 2-3 existing products
            existing_skus = list(state.products.keys())
            num_components = product_rng.integer(2, min(3, len(existing_skus)))
            bundle_components = product_rng.sample(existing_skus, num_components)

        state.products[sku] = ProductState(
            sku=sku,
            name=f"Product {i + 1}",
            category_hierarchy=category.copy(),
            current_price_cents=product_rng.integer(100, 10000),
            is_virtual=is_virtual,
            bundle_components=bundle_components,
        )

    # Generate stores
    store_rng = rng.fork("stores")
    store_count = 0

    if config.stores.physical_stores:
        for i in range(num_stores):
            store_id = f"STORE-{i + 1:03d}"
            state.stores[store_id] = StoreState(
                store_id=store_id,
                store_name=f"Store #{i + 1}",
                channel="physical",
                open_date=state.current_business_date,
                registers=[f"REG-{store_id}-{j + 1}" for j in range(store_rng.integer(2, 5))],
                employees=[f"EMP-{store_id}-{j + 1}" for j in range(store_rng.integer(5, 15))],
            )
            store_count += 1

    if config.stores.online_channel:
        store_id = "ONLINE"
        state.stores[store_id] = StoreState(
            store_id=store_id,
            store_name="Online Store",
            channel="online",
            open_date=state.current_business_date,
            registers=["WEB-1", "WEB-2", "MOBILE-1"],
            employees=[f"EMP-ONLINE-{j + 1}" for j in range(10)],
        )

    # Initialize inventory
    if config.inventory.tracked:
        for store_id in state.stores:
            state.inventory[store_id] = {}
            for sku in state.products:
                state.inventory[store_id][sku] = rng.integer(50, 200)

    # Generate promotions
    promo_rng = rng.fork("promotions")
    for i in range(num_promotions):
        promo_code = f"PROMO-{i + 1:03d}"
        is_basket = config.promotions.basket_level_promotions and promo_rng.boolean(0.3)
        is_stackable = (
            config.promotions.stackable_promotions and promo_rng.boolean(0.4)
        )

        # Select applicable SKUs (or None for all)
        applicable_skus = None
        if not is_basket and promo_rng.boolean(0.7):
            num_skus = promo_rng.integer(1, 10)
            applicable_skus = promo_rng.sample(list(state.products.keys()), num_skus)

        state.promotions[promo_code] = PromotionState(
            promotion_code=promo_code,
            promotion_name=f"Promotion {i + 1}",
            discount_type=promo_rng.choice(["percent", "fixed", "bogo"]),
            discount_value=promo_rng.integer(5, 50),
            applicable_skus=applicable_skus,
            start_date=state.current_business_date,
            end_date=state.current_business_date + timedelta(days=promo_rng.integer(7, 90)),
            is_basket_level=is_basket,
            is_stackable=is_stackable,
        )

    return state
