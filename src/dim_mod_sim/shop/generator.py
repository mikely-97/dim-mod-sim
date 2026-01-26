"""Shop configuration generator."""

from dim_mod_sim.core.random import SeededRandom
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
