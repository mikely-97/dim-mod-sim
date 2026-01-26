"""Shop configuration models using Pydantic."""

from pydantic import BaseModel, ConfigDict, model_validator

from dim_mod_sim.shop.options import (
    CustomerIdReliability,
    InventoryType,
    ProductHierarchyChangeFrequency,
    PromotionsPerLineItem,
    ReturnsPricingPolicy,
    ReturnsReferencePolicy,
    TimestampBusinessDateRelation,
    TransactionGrain,
)


class TransactionConfig(BaseModel):
    """Configuration for transaction recording behavior."""

    model_config = ConfigDict(frozen=True)

    grain: TransactionGrain
    multiple_payments: bool
    voids_enabled: bool
    manual_overrides: bool


class TimeConfig(BaseModel):
    """Configuration for time semantics."""

    model_config = ConfigDict(frozen=True)

    timestamp_business_date_relation: TimestampBusinessDateRelation
    late_arriving_events: bool
    backdated_corrections: bool


class ProductConfig(BaseModel):
    """Configuration for product behavior."""

    model_config = ConfigDict(frozen=True)

    sku_reuse: bool
    hierarchy_change_frequency: ProductHierarchyChangeFrequency
    bundled_products: bool
    virtual_products: bool


class CustomerConfig(BaseModel):
    """Configuration for customer handling."""

    model_config = ConfigDict(frozen=True)

    anonymous_allowed: bool
    customer_id_reliability: CustomerIdReliability
    household_grouping: bool

    @model_validator(mode="after")
    def validate_household_grouping(self) -> "CustomerConfig":
        """Household grouping requires customer ID to exist."""
        if (
            self.household_grouping
            and self.customer_id_reliability == CustomerIdReliability.ABSENT
        ):
            raise ValueError(
                "household_grouping requires customer_id_reliability != ABSENT"
            )
        return self


class StoreConfig(BaseModel):
    """Configuration for store/channel behavior."""

    model_config = ConfigDict(frozen=True)

    physical_stores: bool
    online_channel: bool
    cross_store_returns: bool
    store_lifecycle_changes: bool

    @model_validator(mode="after")
    def validate_channels(self) -> "StoreConfig":
        """At least one channel must be enabled."""
        if not self.physical_stores and not self.online_channel:
            raise ValueError("At least one of physical_stores or online_channel required")
        return self

    @model_validator(mode="after")
    def validate_cross_store_returns(self) -> "StoreConfig":
        """Cross-store returns require physical stores."""
        if self.cross_store_returns and not self.physical_stores:
            raise ValueError("cross_store_returns requires physical_stores")
        return self


class PromotionConfig(BaseModel):
    """Configuration for promotion handling."""

    model_config = ConfigDict(frozen=True)

    promotions_per_line_item: PromotionsPerLineItem
    stackable_promotions: bool
    basket_level_promotions: bool
    post_transaction_promotions: bool

    @model_validator(mode="after")
    def validate_stackable(self) -> "PromotionConfig":
        """Stackable promotions require multiple promotions per line item."""
        if (
            self.stackable_promotions
            and self.promotions_per_line_item == PromotionsPerLineItem.ONE
        ):
            raise ValueError(
                "stackable_promotions requires promotions_per_line_item == MANY"
            )
        return self


class ReturnsConfig(BaseModel):
    """Configuration for returns handling."""

    model_config = ConfigDict(frozen=True)

    reference_policy: ReturnsReferencePolicy
    pricing_policy: ReturnsPricingPolicy


class InventoryConfig(BaseModel):
    """Configuration for inventory tracking."""

    model_config = ConfigDict(frozen=True)

    tracked: bool
    inventory_type: InventoryType | None = None

    @model_validator(mode="after")
    def validate_inventory_type(self) -> "InventoryConfig":
        """Inventory type required if tracked, forbidden if not."""
        if self.tracked and self.inventory_type is None:
            raise ValueError("inventory_type required when tracked=True")
        if not self.tracked and self.inventory_type is not None:
            raise ValueError("inventory_type must be None when tracked=False")
        return self


class ShopConfiguration(BaseModel):
    """Complete configuration for a generated shop."""

    model_config = ConfigDict(frozen=True)

    seed: int
    shop_name: str
    transactions: TransactionConfig
    time: TimeConfig
    products: ProductConfig
    customers: CustomerConfig
    stores: StoreConfig
    promotions: PromotionConfig
    returns: ReturnsConfig
    inventory: InventoryConfig

    def has_returns(self) -> bool:
        """Check if returns are enabled (not NEVER)."""
        return self.returns.reference_policy != ReturnsReferencePolicy.NEVER

    def has_inventory(self) -> bool:
        """Check if inventory tracking is enabled."""
        return self.inventory.tracked

    def has_voids(self) -> bool:
        """Check if void events are enabled."""
        return self.transactions.voids_enabled

    def has_corrections(self) -> bool:
        """Check if backdated corrections are enabled."""
        return self.time.backdated_corrections
