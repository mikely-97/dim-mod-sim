"""Shop configuration generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dim_mod_sim.core.random import SeededRandom

if TYPE_CHECKING:
    from dim_mod_sim.play.framing import EnabledTrap
from dim_mod_sim.shop.config import (
    CustomerConfig,
    InventoryConfig,
    ProductConfig,
    PromotionConfig,
    ReturnsConfig,
    ShopConfiguration,
    StoreConfig,
    TimeConfig,
    TransactionConfig,
)
from dim_mod_sim.shop.options import (
    CustomerIdReliability,
    Difficulty,
    InventoryType,
    ProductHierarchyChangeFrequency,
    PromotionsPerLineItem,
    ReturnsPricingPolicy,
    ReturnsReferencePolicy,
    TimestampBusinessDateRelation,
    TransactionGrain,
)

# Shop name components for generating realistic names
SHOP_NAME_PREFIXES = [
    "Quick", "Fresh", "Daily", "Smart", "Value", "Prime", "Best", "Super",
    "Metro", "Urban", "Corner", "Family", "Golden", "Silver", "Blue", "Green",
]

SHOP_NAME_SUFFIXES = [
    "Mart", "Store", "Shop", "Market", "Goods", "Depot", "Outlet", "Express",
    "Plus", "Hub", "Place", "Stop", "Center", "Corner", "Essentials", "Basics",
]


# Probability weights by difficulty level
# Higher values for options that create more modeling challenges
DIFFICULTY_WEIGHTS: dict[Difficulty, dict[str, dict[str, float]]] = {
    Difficulty.EASY: {
        "transaction_grain": {
            TransactionGrain.LINE_ITEM_LEVEL.value: 0.9,
            TransactionGrain.RECEIPT_LEVEL.value: 0.1,
            TransactionGrain.MIXED.value: 0.0,
        },
        "timestamp_relation": {
            TimestampBusinessDateRelation.SAME.value: 0.9,
            TimestampBusinessDateRelation.DIFFERENT.value: 0.1,
        },
        "hierarchy_changes": {
            ProductHierarchyChangeFrequency.NONE.value: 0.8,
            ProductHierarchyChangeFrequency.OCCASIONAL.value: 0.2,
            ProductHierarchyChangeFrequency.FREQUENT.value: 0.0,
        },
        "customer_reliability": {
            CustomerIdReliability.RELIABLE.value: 0.8,
            CustomerIdReliability.UNRELIABLE.value: 0.1,
            CustomerIdReliability.ABSENT.value: 0.1,
        },
        "returns_reference": {
            ReturnsReferencePolicy.ALWAYS.value: 0.8,
            ReturnsReferencePolicy.SOMETIMES.value: 0.1,
            ReturnsReferencePolicy.NEVER.value: 0.1,
        },
        "returns_pricing": {
            ReturnsPricingPolicy.ORIGINAL_PRICE.value: 0.9,
            ReturnsPricingPolicy.CURRENT_PRICE.value: 0.1,
            ReturnsPricingPolicy.ARBITRARY_OVERRIDE.value: 0.0,
        },
        "promotions_per_item": {
            PromotionsPerLineItem.ONE.value: 0.9,
            PromotionsPerLineItem.MANY.value: 0.1,
        },
        "inventory_type": {
            InventoryType.TRANSACTIONAL.value: 0.8,
            InventoryType.PERIODIC_SNAPSHOT.value: 0.2,
            InventoryType.BOTH.value: 0.0,
        },
        "boolean_true_prob": 0.3,  # Less likely to enable complex features
    },
    Difficulty.MEDIUM: {
        "transaction_grain": {
            TransactionGrain.LINE_ITEM_LEVEL.value: 0.6,
            TransactionGrain.RECEIPT_LEVEL.value: 0.2,
            TransactionGrain.MIXED.value: 0.2,
        },
        "timestamp_relation": {
            TimestampBusinessDateRelation.SAME.value: 0.5,
            TimestampBusinessDateRelation.DIFFERENT.value: 0.5,
        },
        "hierarchy_changes": {
            ProductHierarchyChangeFrequency.NONE.value: 0.4,
            ProductHierarchyChangeFrequency.OCCASIONAL.value: 0.4,
            ProductHierarchyChangeFrequency.FREQUENT.value: 0.2,
        },
        "customer_reliability": {
            CustomerIdReliability.RELIABLE.value: 0.5,
            CustomerIdReliability.UNRELIABLE.value: 0.3,
            CustomerIdReliability.ABSENT.value: 0.2,
        },
        "returns_reference": {
            ReturnsReferencePolicy.ALWAYS.value: 0.4,
            ReturnsReferencePolicy.SOMETIMES.value: 0.4,
            ReturnsReferencePolicy.NEVER.value: 0.2,
        },
        "returns_pricing": {
            ReturnsPricingPolicy.ORIGINAL_PRICE.value: 0.5,
            ReturnsPricingPolicy.CURRENT_PRICE.value: 0.3,
            ReturnsPricingPolicy.ARBITRARY_OVERRIDE.value: 0.2,
        },
        "promotions_per_item": {
            PromotionsPerLineItem.ONE.value: 0.5,
            PromotionsPerLineItem.MANY.value: 0.5,
        },
        "inventory_type": {
            InventoryType.TRANSACTIONAL.value: 0.4,
            InventoryType.PERIODIC_SNAPSHOT.value: 0.4,
            InventoryType.BOTH.value: 0.2,
        },
        "boolean_true_prob": 0.5,
    },
    Difficulty.HARD: {
        "transaction_grain": {
            TransactionGrain.LINE_ITEM_LEVEL.value: 0.3,
            TransactionGrain.RECEIPT_LEVEL.value: 0.3,
            TransactionGrain.MIXED.value: 0.4,
        },
        "timestamp_relation": {
            TimestampBusinessDateRelation.SAME.value: 0.2,
            TimestampBusinessDateRelation.DIFFERENT.value: 0.8,
        },
        "hierarchy_changes": {
            ProductHierarchyChangeFrequency.NONE.value: 0.1,
            ProductHierarchyChangeFrequency.OCCASIONAL.value: 0.3,
            ProductHierarchyChangeFrequency.FREQUENT.value: 0.6,
        },
        "customer_reliability": {
            CustomerIdReliability.RELIABLE.value: 0.2,
            CustomerIdReliability.UNRELIABLE.value: 0.5,
            CustomerIdReliability.ABSENT.value: 0.3,
        },
        "returns_reference": {
            ReturnsReferencePolicy.ALWAYS.value: 0.2,
            ReturnsReferencePolicy.SOMETIMES.value: 0.5,
            ReturnsReferencePolicy.NEVER.value: 0.3,
        },
        "returns_pricing": {
            ReturnsPricingPolicy.ORIGINAL_PRICE.value: 0.2,
            ReturnsPricingPolicy.CURRENT_PRICE.value: 0.3,
            ReturnsPricingPolicy.ARBITRARY_OVERRIDE.value: 0.5,
        },
        "promotions_per_item": {
            PromotionsPerLineItem.ONE.value: 0.2,
            PromotionsPerLineItem.MANY.value: 0.8,
        },
        "inventory_type": {
            InventoryType.TRANSACTIONAL.value: 0.2,
            InventoryType.PERIODIC_SNAPSHOT.value: 0.2,
            InventoryType.BOTH.value: 0.6,
        },
        "boolean_true_prob": 0.7,
    },
    Difficulty.ADVERSARIAL: {
        "transaction_grain": {
            TransactionGrain.LINE_ITEM_LEVEL.value: 0.1,
            TransactionGrain.RECEIPT_LEVEL.value: 0.2,
            TransactionGrain.MIXED.value: 0.7,
        },
        "timestamp_relation": {
            TimestampBusinessDateRelation.SAME.value: 0.1,
            TimestampBusinessDateRelation.DIFFERENT.value: 0.9,
        },
        "hierarchy_changes": {
            ProductHierarchyChangeFrequency.NONE.value: 0.0,
            ProductHierarchyChangeFrequency.OCCASIONAL.value: 0.2,
            ProductHierarchyChangeFrequency.FREQUENT.value: 0.8,
        },
        "customer_reliability": {
            CustomerIdReliability.RELIABLE.value: 0.1,
            CustomerIdReliability.UNRELIABLE.value: 0.6,
            CustomerIdReliability.ABSENT.value: 0.3,
        },
        "returns_reference": {
            ReturnsReferencePolicy.ALWAYS.value: 0.1,
            ReturnsReferencePolicy.SOMETIMES.value: 0.6,
            ReturnsReferencePolicy.NEVER.value: 0.3,
        },
        "returns_pricing": {
            ReturnsPricingPolicy.ORIGINAL_PRICE.value: 0.1,
            ReturnsPricingPolicy.CURRENT_PRICE.value: 0.2,
            ReturnsPricingPolicy.ARBITRARY_OVERRIDE.value: 0.7,
        },
        "promotions_per_item": {
            PromotionsPerLineItem.ONE.value: 0.1,
            PromotionsPerLineItem.MANY.value: 0.9,
        },
        "inventory_type": {
            InventoryType.TRANSACTIONAL.value: 0.1,
            InventoryType.PERIODIC_SNAPSHOT.value: 0.1,
            InventoryType.BOTH.value: 0.8,
        },
        "boolean_true_prob": 0.85,
    },
}


class ShopGenerator:
    """Generates shop configurations deterministically from a seed."""

    def __init__(self, seed: int, difficulty: Difficulty = Difficulty.MEDIUM) -> None:
        self.seed = seed
        self.difficulty = difficulty
        self.rng = SeededRandom(seed)
        self.weights = DIFFICULTY_WEIGHTS[difficulty]

    def generate(self) -> ShopConfiguration:
        """Generate a valid shop configuration."""
        shop_name = self._generate_shop_name()
        transactions = self._generate_transactions()
        time = self._generate_time()
        products = self._generate_products()
        customers = self._generate_customers()
        stores = self._generate_stores()
        promotions = self._generate_promotions()
        returns = self._generate_returns()
        inventory = self._generate_inventory()

        return ShopConfiguration(
            seed=self.seed,
            shop_name=shop_name,
            transactions=transactions,
            time=time,
            products=products,
            customers=customers,
            stores=stores,
            promotions=promotions,
            returns=returns,
            inventory=inventory,
        )

    def _generate_shop_name(self) -> str:
        """Generate a realistic shop name."""
        rng = self.rng.fork("shop_name")
        prefix = rng.choice(SHOP_NAME_PREFIXES)
        suffix = rng.choice(SHOP_NAME_SUFFIXES)
        return f"{prefix} {suffix}"

    def _weighted_enum_choice(
        self, rng: SeededRandom, weight_key: str, enum_class: type
    ) -> str:
        """Select an enum value using difficulty weights."""
        weights_dict = self.weights[weight_key]
        options = list(weights_dict.keys())
        weights = [weights_dict[o] for o in options]
        return rng.weighted_choice(options, weights)

    def _generate_transactions(self) -> TransactionConfig:
        """Generate transaction configuration."""
        rng = self.rng.fork("transactions")
        prob = self.weights["boolean_true_prob"]

        grain_value = self._weighted_enum_choice(rng, "transaction_grain", TransactionGrain)

        return TransactionConfig(
            grain=TransactionGrain(grain_value),
            multiple_payments=rng.boolean(prob),
            voids_enabled=rng.boolean(prob),
            manual_overrides=rng.boolean(prob * 0.7),  # Less common
        )

    def _generate_time(self) -> TimeConfig:
        """Generate time semantics configuration."""
        rng = self.rng.fork("time")
        prob = self.weights["boolean_true_prob"]

        relation_value = self._weighted_enum_choice(
            rng, "timestamp_relation", TimestampBusinessDateRelation
        )

        return TimeConfig(
            timestamp_business_date_relation=TimestampBusinessDateRelation(relation_value),
            late_arriving_events=rng.boolean(prob),
            backdated_corrections=rng.boolean(prob * 0.6),  # Less common
        )

    def _generate_products(self) -> ProductConfig:
        """Generate product configuration."""
        rng = self.rng.fork("products")
        prob = self.weights["boolean_true_prob"]

        hierarchy_value = self._weighted_enum_choice(
            rng, "hierarchy_changes", ProductHierarchyChangeFrequency
        )

        return ProductConfig(
            sku_reuse=rng.boolean(prob * 0.5),  # Modeling trap
            hierarchy_change_frequency=ProductHierarchyChangeFrequency(hierarchy_value),
            bundled_products=rng.boolean(prob * 0.6),
            virtual_products=rng.boolean(prob * 0.7),
        )

    def _generate_customers(self) -> CustomerConfig:
        """Generate customer configuration."""
        rng = self.rng.fork("customers")
        prob = self.weights["boolean_true_prob"]

        reliability_value = self._weighted_enum_choice(
            rng, "customer_reliability", CustomerIdReliability
        )
        reliability = CustomerIdReliability(reliability_value)

        # Household grouping only possible if customer ID exists
        can_have_households = reliability != CustomerIdReliability.ABSENT
        household_grouping = can_have_households and rng.boolean(prob * 0.5)

        return CustomerConfig(
            anonymous_allowed=rng.boolean(prob),
            customer_id_reliability=reliability,
            household_grouping=household_grouping,
        )

    def _generate_stores(self) -> StoreConfig:
        """Generate store/channel configuration."""
        rng = self.rng.fork("stores")
        prob = self.weights["boolean_true_prob"]

        # Ensure at least one channel
        physical = rng.boolean(prob)
        online = rng.boolean(prob)
        if not physical and not online:
            # Force one on
            if rng.boolean(0.5):
                physical = True
            else:
                online = True

        # Cross-store returns only if physical stores exist
        cross_store = physical and rng.boolean(prob * 0.6)

        return StoreConfig(
            physical_stores=physical,
            online_channel=online,
            cross_store_returns=cross_store,
            store_lifecycle_changes=rng.boolean(prob * 0.4),
        )

    def _generate_promotions(self) -> PromotionConfig:
        """Generate promotion configuration."""
        rng = self.rng.fork("promotions")
        prob = self.weights["boolean_true_prob"]

        per_item_value = self._weighted_enum_choice(
            rng, "promotions_per_item", PromotionsPerLineItem
        )
        per_item = PromotionsPerLineItem(per_item_value)

        # Stackable only if multiple promotions allowed
        can_stack = per_item == PromotionsPerLineItem.MANY
        stackable = can_stack and rng.boolean(prob)

        return PromotionConfig(
            promotions_per_line_item=per_item,
            stackable_promotions=stackable,
            basket_level_promotions=rng.boolean(prob),
            post_transaction_promotions=rng.boolean(prob * 0.4),  # Unusual
        )

    def _generate_returns(self) -> ReturnsConfig:
        """Generate returns configuration."""
        rng = self.rng.fork("returns")

        reference_value = self._weighted_enum_choice(
            rng, "returns_reference", ReturnsReferencePolicy
        )
        pricing_value = self._weighted_enum_choice(
            rng, "returns_pricing", ReturnsPricingPolicy
        )

        return ReturnsConfig(
            reference_policy=ReturnsReferencePolicy(reference_value),
            pricing_policy=ReturnsPricingPolicy(pricing_value),
        )

    def _generate_inventory(self) -> InventoryConfig:
        """Generate inventory configuration."""
        rng = self.rng.fork("inventory")
        prob = self.weights["boolean_true_prob"]

        tracked = rng.boolean(prob)

        if tracked:
            inv_type_value = self._weighted_enum_choice(
                rng, "inventory_type", InventoryType
            )
            inv_type = InventoryType(inv_type_value)
        else:
            inv_type = None

        return InventoryConfig(
            tracked=tracked,
            inventory_type=inv_type,
        )


def extract_enabled_traps(config: ShopConfiguration) -> list["EnabledTrap"]:
    """Extract list of enabled modeling traps from a shop configuration.

    This analyzes the configuration and identifies which traps are active
    that could trip up a naive dimensional modeler.
    """
    from dim_mod_sim.play.framing import EnabledTrap, TrapCategory

    traps: list[EnabledTrap] = []

    # === GRAIN TRAPS ===
    if config.transactions.grain == TransactionGrain.MIXED:
        traps.append(EnabledTrap(
            category=TrapCategory.GRAIN,
            name="Mixed Transaction Grain",
            threat_description="mixing line-item and receipt-level transactions unpredictably",
            config_source="transactions.grain=mixed",
        ))

    if config.transactions.multiple_payments:
        traps.append(EnabledTrap(
            category=TrapCategory.GRAIN,
            name="Multiple Payments",
            threat_description="splitting payments across multiple tender types per transaction",
            config_source="transactions.multiple_payments=true",
        ))

    if config.promotions.promotions_per_line_item == PromotionsPerLineItem.MANY:
        traps.append(EnabledTrap(
            category=TrapCategory.GRAIN,
            name="Multiple Promotions Per Item",
            threat_description="stacking multiple promotions on single line items",
            config_source="promotions.promotions_per_line_item=many",
        ))

    # === TEMPORAL TRAPS ===
    if config.time.timestamp_business_date_relation == TimestampBusinessDateRelation.DIFFERENT:
        traps.append(EnabledTrap(
            category=TrapCategory.TEMPORAL,
            name="Timestamp/Business Date Divergence",
            threat_description="recording events at midnight that belong to yesterday's business",
            config_source="time.timestamp_business_date_relation=different",
        ))

    if config.time.backdated_corrections:
        traps.append(EnabledTrap(
            category=TrapCategory.TEMPORAL,
            name="Backdated Corrections",
            threat_description="recording corrections today that apply to last week's transactions",
            config_source="time.backdated_corrections=true",
        ))

    if config.time.late_arriving_events:
        traps.append(EnabledTrap(
            category=TrapCategory.TEMPORAL,
            name="Late-Arriving Events",
            threat_description="processing events days after they actually occurred",
            config_source="time.late_arriving_events=true",
        ))

    if config.products.hierarchy_change_frequency != ProductHierarchyChangeFrequency.NONE:
        freq = config.products.hierarchy_change_frequency.value
        traps.append(EnabledTrap(
            category=TrapCategory.TEMPORAL,
            name="Product Hierarchy Changes",
            threat_description=f"reorganizing product categories {freq}",
            config_source=f"products.hierarchy_change_frequency={freq}",
        ))

    # === IDENTITY TRAPS ===
    if config.customers.customer_id_reliability == CustomerIdReliability.UNRELIABLE:
        traps.append(EnabledTrap(
            category=TrapCategory.IDENTITY,
            name="Unreliable Customer IDs",
            threat_description="giving you customer IDs that merge and split randomly",
            config_source="customers.customer_id_reliability=unreliable",
        ))

    if config.customers.customer_id_reliability == CustomerIdReliability.ABSENT:
        traps.append(EnabledTrap(
            category=TrapCategory.IDENTITY,
            name="No Customer IDs",
            threat_description="having no customer identifiers at all",
            config_source="customers.customer_id_reliability=absent",
        ))

    if config.products.sku_reuse:
        traps.append(EnabledTrap(
            category=TrapCategory.IDENTITY,
            name="SKU Reuse",
            threat_description="reusing SKU codes for completely different products over time",
            config_source="products.sku_reuse=true",
        ))

    # === SEMANTIC TRAPS ===
    if config.returns.reference_policy == ReturnsReferencePolicy.SOMETIMES:
        traps.append(EnabledTrap(
            category=TrapCategory.SEMANTIC,
            name="Optional Return References",
            threat_description="sometimes referencing original sales on returns, sometimes not",
            config_source="returns.reference_policy=sometimes",
        ))

    if config.returns.reference_policy == ReturnsReferencePolicy.NEVER:
        traps.append(EnabledTrap(
            category=TrapCategory.SEMANTIC,
            name="Orphan Returns",
            threat_description="accepting returns with no link to original transactions",
            config_source="returns.reference_policy=never",
        ))

    if config.returns.pricing_policy == ReturnsPricingPolicy.ARBITRARY_OVERRIDE:
        traps.append(EnabledTrap(
            category=TrapCategory.SEMANTIC,
            name="Arbitrary Return Pricing",
            threat_description="overriding return prices with values matching nothing in the system",
            config_source="returns.pricing_policy=arbitrary_override",
        ))

    if config.transactions.voids_enabled:
        traps.append(EnabledTrap(
            category=TrapCategory.SEMANTIC,
            name="Transaction Voids",
            threat_description="voiding transactions after the fact",
            config_source="transactions.voids_enabled=true",
        ))

    if config.transactions.manual_overrides:
        traps.append(EnabledTrap(
            category=TrapCategory.SEMANTIC,
            name="Manual Price Overrides",
            threat_description="letting cashiers override prices at the register",
            config_source="transactions.manual_overrides=true",
        ))

    # === RELATIONSHIP TRAPS ===
    if config.stores.cross_store_returns:
        traps.append(EnabledTrap(
            category=TrapCategory.RELATIONSHIP,
            name="Cross-Store Returns",
            threat_description="allowing items bought at one store to be returned at another",
            config_source="stores.cross_store_returns=true",
        ))

    if config.stores.store_lifecycle_changes:
        traps.append(EnabledTrap(
            category=TrapCategory.RELATIONSHIP,
            name="Store Lifecycle Changes",
            threat_description="opening, closing, and merging stores over time",
            config_source="stores.store_lifecycle_changes=true",
        ))

    if config.customers.household_grouping:
        traps.append(EnabledTrap(
            category=TrapCategory.RELATIONSHIP,
            name="Household Grouping",
            threat_description="grouping customers into households that can change",
            config_source="customers.household_grouping=true",
        ))

    if config.products.bundled_products:
        traps.append(EnabledTrap(
            category=TrapCategory.RELATIONSHIP,
            name="Bundled Products",
            threat_description="selling products as bundles with complex component tracking",
            config_source="products.bundled_products=true",
        ))

    return traps
