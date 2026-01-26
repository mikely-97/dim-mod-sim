"""Description generator for shop configurations."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from dim_mod_sim.core.random import SeededRandom
from dim_mod_sim.description.prose import ProseVariations
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import (
    CustomerIdReliability,
    PromotionsPerLineItem,
    TransactionGrain,
)


class DescriptionGenerator:
    """Generates human-readable shop descriptions."""

    def __init__(self, config: ShopConfiguration) -> None:
        self.config = config
        self.rng = SeededRandom(config.seed)
        self.prose = ProseVariations(self.rng.fork("prose"))

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self) -> str:
        """Generate the complete shop description."""
        template = self.env.get_template("shop.j2")

        return template.render(
            shop_name=self.config.shop_name,
            sections=self._generate_sections(),
        )

    def _generate_sections(self) -> dict[str, str]:
        """Generate each section of the description."""
        return {
            "transactions": self._describe_transactions(),
            "time_semantics": self._describe_time_semantics(),
            "products": self._describe_products(),
            "customers": self._describe_customers(),
            "stores": self._describe_stores(),
            "promotions": self._describe_promotions(),
            "returns": self._describe_returns(),
            "inventory": self._describe_inventory(),
        }

    def _describe_transactions(self) -> str:
        """Generate transaction section."""
        template = self.env.get_template("transactions.j2")
        cfg = self.config.transactions

        return template.render(
            shop_name=self.config.shop_name,
            grain_phrase=self.prose.get_phrase("transaction_grain", cfg.grain.value),
            multiple_payments_phrase=self.prose.get_phrase(
                "multiple_payments", cfg.multiple_payments
            ),
            voids_enabled=cfg.voids_enabled,
            voids_phrase=self.prose.get_phrase("voids", cfg.voids_enabled),
            manual_overrides=cfg.manual_overrides,
            ambiguities=self._identify_transaction_ambiguities(),
        )

    def _identify_transaction_ambiguities(self) -> list[str]:
        """Identify ambiguities in transaction handling."""
        ambiguities = []
        cfg = self.config.transactions

        if cfg.grain == TransactionGrain.MIXED:
            ambiguities.append(
                "There is no reliable indicator of whether a given transaction "
                "record contains aggregated or itemized data."
            )

        if cfg.multiple_payments and cfg.voids_enabled:
            ambiguities.append(
                "When a transaction with multiple payments is voided, the "
                "relationship between individual payment voids is not explicit."
            )

        if cfg.manual_overrides:
            ambiguities.append(
                "Manual overrides are not always distinguishable from legitimate "
                "promotions in the data."
            )

        return ambiguities

    def _describe_time_semantics(self) -> str:
        """Generate time semantics section."""
        template = self.env.get_template("time_semantics.j2")
        cfg = self.config.time

        return template.render(
            timestamp_relation_phrase=self.prose.get_phrase(
                "timestamp_relation", cfg.timestamp_business_date_relation.value
            ),
            late_arriving_events=cfg.late_arriving_events,
            late_arriving_phrase=self.prose.get_phrase(
                "late_arriving", cfg.late_arriving_events
            ),
            backdated_corrections=cfg.backdated_corrections,
            backdated_corrections_phrase=self.prose.get_phrase(
                "backdated_corrections", cfg.backdated_corrections
            ),
            ambiguities=self._identify_time_ambiguities(),
        )

    def _identify_time_ambiguities(self) -> list[str]:
        """Identify ambiguities in time handling."""
        ambiguities = []
        cfg = self.config.time

        if cfg.timestamp_business_date_relation.value == "different":
            ambiguities.append(
                "The mapping between transaction timestamps and business dates is "
                "not deterministic; two transactions with the same timestamp might "
                "have different business dates."
            )

        if cfg.late_arriving_events and cfg.backdated_corrections:
            ambiguities.append(
                "It can be difficult to distinguish between a late-arriving event "
                "and a backdated correction without examining the full context."
            )

        return ambiguities

    def _describe_products(self) -> str:
        """Generate products section."""
        template = self.env.get_template("products.j2")
        cfg = self.config.products

        return template.render(
            sku_reuse=cfg.sku_reuse,
            sku_reuse_phrase=self.prose.get_phrase("sku_reuse", cfg.sku_reuse),
            hierarchy_change_phrase=self.prose.get_phrase(
                "hierarchy_change", cfg.hierarchy_change_frequency.value
            ),
            bundled_products=cfg.bundled_products,
            virtual_products=cfg.virtual_products,
            ambiguities=self._identify_product_ambiguities(),
        )

    def _identify_product_ambiguities(self) -> list[str]:
        """Identify ambiguities in product handling."""
        ambiguities = []
        cfg = self.config.products

        if cfg.sku_reuse:
            ambiguities.append(
                "When joining transactions to product master data, you must "
                "consider point-in-time accuracy since SKUs may refer to "
                "different products over time."
            )

        if cfg.bundled_products:
            ambiguities.append(
                "Bundle sales may be recorded at the bundle level, component "
                "level, or both. The recording method is not always consistent."
            )

        return ambiguities

    def _describe_customers(self) -> str:
        """Generate customers section."""
        template = self.env.get_template("customers.j2")
        cfg = self.config.customers

        return template.render(
            customer_reliability=cfg.customer_id_reliability.value,
            customer_reliability_phrase=self.prose.get_phrase(
                "customer_reliability", cfg.customer_id_reliability.value
            ),
            anonymous_allowed=cfg.anonymous_allowed,
            household_grouping=cfg.household_grouping,
            ambiguities=self._identify_customer_ambiguities(),
        )

    def _identify_customer_ambiguities(self) -> list[str]:
        """Identify ambiguities in customer handling."""
        ambiguities = []
        cfg = self.config.customers

        if cfg.customer_id_reliability == CustomerIdReliability.UNRELIABLE:
            ambiguities.append(
                "Customer analytics should account for both split identities "
                "(one person with multiple IDs) and merged identities (multiple "
                "people sharing an ID)."
            )

        if cfg.anonymous_allowed and cfg.customer_id_reliability != CustomerIdReliability.ABSENT:
            ambiguities.append(
                "A NULL customer ID could mean an anonymous purchase or a failure "
                "to capture the ID; these cases are not distinguished."
            )

        if cfg.household_grouping:
            ambiguities.append(
                "Household assignments may change over time. The current household "
                "structure may not reflect historical living arrangements."
            )

        return ambiguities

    def _describe_stores(self) -> str:
        """Generate stores section."""
        template = self.env.get_template("stores.j2")
        cfg = self.config.stores

        return template.render(
            shop_name=self.config.shop_name,
            physical_stores=cfg.physical_stores,
            online_channel=cfg.online_channel,
            cross_store_returns=cfg.cross_store_returns,
            store_lifecycle_changes=cfg.store_lifecycle_changes,
            ambiguities=self._identify_store_ambiguities(),
        )

    def _identify_store_ambiguities(self) -> list[str]:
        """Identify ambiguities in store handling."""
        ambiguities = []
        cfg = self.config.stores

        if cfg.store_lifecycle_changes:
            ambiguities.append(
                "When stores merge, historical transactions may reference the "
                "old store ID even though the store no longer exists."
            )

        if cfg.physical_stores and cfg.online_channel:
            ambiguities.append(
                "Some transactions may be ambiguous in terms of channel "
                "(e.g., buy-online-pickup-in-store)."
            )

        return ambiguities

    def _describe_promotions(self) -> str:
        """Generate promotions section."""
        template = self.env.get_template("promotions.j2")
        cfg = self.config.promotions

        return template.render(
            promotions_per_line_item=cfg.promotions_per_line_item.value,
            stackable_promotions=cfg.stackable_promotions,
            basket_level_promotions=cfg.basket_level_promotions,
            post_transaction_promotions=cfg.post_transaction_promotions,
            ambiguities=self._identify_promotion_ambiguities(),
        )

    def _identify_promotion_ambiguities(self) -> list[str]:
        """Identify ambiguities in promotion handling."""
        ambiguities = []
        cfg = self.config.promotions

        if cfg.promotions_per_line_item == PromotionsPerLineItem.MANY:
            ambiguities.append(
                "When multiple promotions apply to a line item, the individual "
                "contribution of each promotion to the discount may not be clear."
            )

        if cfg.basket_level_promotions:
            ambiguities.append(
                "Basket-level discounts are not allocated to individual line "
                "items, making true unit economics difficult to calculate."
            )

        if cfg.post_transaction_promotions:
            ambiguities.append(
                "Post-transaction promotions may create adjustment events that "
                "complicate revenue calculations."
            )

        return ambiguities

    def _describe_returns(self) -> str:
        """Generate returns section."""
        template = self.env.get_template("returns.j2")
        cfg = self.config.returns

        return template.render(
            returns_reference_phrase=self.prose.get_phrase(
                "returns_reference", cfg.reference_policy.value
            ),
            returns_pricing_phrase=self.prose.get_phrase(
                "returns_pricing", cfg.pricing_policy.value
            ),
            ambiguities=self._identify_returns_ambiguities(),
        )

    def _identify_returns_ambiguities(self) -> list[str]:
        """Identify ambiguities in returns handling."""
        ambiguities = []
        cfg = self.config.returns

        if cfg.reference_policy.value == "sometimes":
            ambiguities.append(
                "Returns without original transaction references cannot be "
                "reliably matched to their originating sales."
            )

        if cfg.pricing_policy.value == "arbitrary_override":
            ambiguities.append(
                "Return prices may not match any price in the system, making "
                "it impossible to validate return amounts programmatically."
            )

        return ambiguities

    def _describe_inventory(self) -> str:
        """Generate inventory section."""
        template = self.env.get_template("inventory.j2")
        cfg = self.config.inventory

        inv_type = cfg.inventory_type.value if cfg.inventory_type else None

        return template.render(
            tracked=cfg.tracked,
            inventory_type=inv_type,
            inventory_type_phrase=self.prose.get_phrase(
                "inventory_type", inv_type
            ) if inv_type else "",
            ambiguities=self._identify_inventory_ambiguities(),
        )

    def _identify_inventory_ambiguities(self) -> list[str]:
        """Identify ambiguities in inventory handling."""
        ambiguities = []
        cfg = self.config.inventory

        if cfg.tracked and cfg.inventory_type and cfg.inventory_type.value == "both":
            ambiguities.append(
                "Transactional inventory events and periodic snapshots may not "
                "always reconcile due to timing differences and untracked adjustments."
            )

        return ambiguities
