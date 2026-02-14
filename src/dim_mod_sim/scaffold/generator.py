"""Schema scaffold generator."""

from typing import Any

from dim_mod_sim.scaffold.models import ScaffoldedSchema, ScaffoldTodo
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import (
    CustomerIdReliability,
    InventoryType,
    ProductHierarchyChangeFrequency,
    PromotionsPerLineItem,
    ReturnsReferencePolicy,
    TransactionGrain,
)


class ScaffoldGenerator:
    """Generates schema scaffolds from shop configurations.

    The scaffold provides structure and TODOs, but NOT correct modeling decisions.
    It uses intentionally questionable defaults that need to be changed.
    """

    def __init__(self, config: ShopConfiguration) -> None:
        self.config = config

    def generate(self) -> ScaffoldedSchema:
        """Generate a schema scaffold with TODOs and warnings."""
        scaffold = ScaffoldedSchema()

        # Core fact tables
        self._add_sales_fact(scaffold)
        self._add_returns_fact(scaffold)
        self._add_inventory_fact(scaffold)

        # Core dimensions
        self._add_date_dimension(scaffold)
        self._add_product_dimension(scaffold)
        self._add_store_dimension(scaffold)
        self._add_customer_dimension(scaffold)

        # Relationships
        self._add_relationships(scaffold)

        # Add global warnings
        self._add_global_warnings(scaffold)

        return scaffold

    def _add_sales_fact(self, scaffold: ScaffoldedSchema) -> None:
        """Add sales fact table scaffold."""
        grain = self.config.transactions.grain

        # Intentionally questionable grain columns
        grain_columns = [
            {"name": "transaction_id", "is_degenerate": True},
        ]

        # Add line_number but mark it as TODO if grain is mixed
        if grain in (TransactionGrain.LINE_ITEM_LEVEL, TransactionGrain.MIXED):
            grain_columns.append({
                "name": "line_number",
                "is_degenerate": True,
                "_todo": "Remove if receipt-level only" if grain == TransactionGrain.MIXED else None,
            })

        fact = {
            "name": "fact_sales",
            "grain_description": "TODO: Define grain - ",
            "grain_columns": grain_columns,
            "measures": [
                {"name": "quantity", "data_type": "int", "aggregation": "sum"},
                {"name": "gross_amount_cents", "data_type": "int", "aggregation": "sum"},
                {"name": "discount_cents", "data_type": "int", "aggregation": "sum"},
                {"name": "net_amount_cents", "data_type": "int", "aggregation": "sum"},
            ],
            "dimension_keys": ["date_key", "product_key", "store_key", "customer_key"],
        }

        # Add grain-specific TODO
        if grain == TransactionGrain.MIXED:
            fact["grain_description"] = "TODO: Define grain - shop uses MIXED transaction levels!"
            fact["_warning"] = "Mixed grain is tricky - consider separate facts per grain"
            scaffold.todos.append(ScaffoldTodo(
                location="fact_sales.grain_description",
                question="How will you handle mixed line-item and receipt-level transactions?",
                hints=[
                    "Option 1: Separate fact tables (fact_sales_line, fact_sales_receipt)",
                    "Option 2: Lowest common grain with is_aggregated flag",
                    "Option 3: Always use line-item grain, synthesize lines for receipts",
                ],
                decision_type="grain",
            ))
        elif grain == TransactionGrain.LINE_ITEM_LEVEL:
            fact["grain_description"] = "TODO: One row per line item sold"
        else:
            fact["grain_description"] = "TODO: One row per transaction/receipt"
            # Remove line_number for receipt-level
            fact["grain_columns"] = [gc for gc in grain_columns if gc["name"] != "line_number"]

        # Multiple payments TODO
        if self.config.transactions.multiple_payments:
            fact["_todo_payments"] = "Multiple payments per transaction - consider separate payment fact"
            scaffold.todos.append(ScaffoldTodo(
                location="fact_sales",
                question="How will you model multiple payments per transaction?",
                hints=[
                    "Option 1: Separate fact_payments table",
                    "Option 2: Bridge table between fact_sales and dim_payment_method",
                    "Option 3: Denormalized payment columns (payment_1, payment_2...)",
                ],
                decision_type="relationship",
            ))

        scaffold.fact_tables.append(fact)

    def _add_returns_fact(self, scaffold: ScaffoldedSchema) -> None:
        """Add returns fact table scaffold if returns are enabled."""
        if self.config.returns.reference_policy == ReturnsReferencePolicy.NEVER:
            return

        fact = {
            "name": "fact_returns",
            "grain_description": "TODO: One row per return line item",
            "grain_columns": [
                {"name": "return_id", "is_degenerate": True},
                {"name": "line_number", "is_degenerate": True},
            ],
            "measures": [
                {"name": "quantity_returned", "data_type": "int", "aggregation": "sum"},
                {"name": "refund_amount_cents", "data_type": "int", "aggregation": "sum"},
            ],
            "dimension_keys": ["date_key", "product_key", "store_key", "customer_key"],
        }

        # Original transaction reference
        if self.config.returns.reference_policy == ReturnsReferencePolicy.ALWAYS:
            fact["grain_columns"].append({
                "name": "original_transaction_id",
                "references_dimension": None,
                "is_degenerate": True,
            })
            fact["_todo_original_ref"] = "Always has original transaction - consider FK to fact_sales"
        elif self.config.returns.reference_policy == ReturnsReferencePolicy.SOMETIMES:
            fact["_warning"] = "Returns SOMETIMES reference original sales - handle NULLs!"
            scaffold.todos.append(ScaffoldTodo(
                location="fact_returns.original_transaction_id",
                question="How will you handle returns that don't reference original transactions?",
                hints=[
                    "Nullable FK to fact_sales",
                    "Separate handling for orphan returns",
                    "Special 'unknown_transaction' surrogate",
                ],
                decision_type="relationship",
            ))

        scaffold.fact_tables.append(fact)

    def _add_inventory_fact(self, scaffold: ScaffoldedSchema) -> None:
        """Add inventory fact table scaffold if inventory is tracked."""
        if not self.config.inventory.tracked:
            return

        inv_type = self.config.inventory.inventory_type

        if inv_type in (InventoryType.TRANSACTIONAL, InventoryType.BOTH):
            scaffold.fact_tables.append({
                "name": "fact_inventory_transactions",
                "grain_description": "TODO: One row per inventory movement",
                "grain_columns": [
                    {"name": "movement_id", "is_degenerate": True},
                ],
                "measures": [
                    {"name": "quantity_change", "data_type": "int", "aggregation": "sum"},
                ],
                "dimension_keys": ["date_key", "product_key", "store_key"],
            })

        if inv_type in (InventoryType.PERIODIC_SNAPSHOT, InventoryType.BOTH):
            scaffold.fact_tables.append({
                "name": "fact_inventory_snapshot",
                "grain_description": "TODO: One row per product-store-date",
                "grain_columns": [
                    {"name": "snapshot_date_key", "references_dimension": "date_key"},
                    {"name": "product_key", "references_dimension": "product_key"},
                    {"name": "store_key", "references_dimension": "store_key"},
                ],
                "measures": [
                    {"name": "quantity_on_hand", "data_type": "int", "aggregation": "sum"},
                ],
                "dimension_keys": ["date_key", "product_key", "store_key"],
                "_note": "Periodic snapshot - semi-additive across time",
            })

        if inv_type == InventoryType.BOTH:
            scaffold.todos.append(ScaffoldTodo(
                location="inventory",
                question="How do transactional and snapshot inventory facts relate?",
                hints=[
                    "Transactional: individual movements",
                    "Snapshot: point-in-time balances",
                    "They serve different query patterns",
                ],
                decision_type="grain",
            ))

    def _add_date_dimension(self, scaffold: ScaffoldedSchema) -> None:
        """Add date dimension scaffold."""
        dim = {
            "name": "dim_date",
            "natural_key": ["date_value"],
            "surrogate_key": "date_key",
            "scd_strategy": "type_0",  # Dates don't change
            "attributes": [
                {"name": "date_value", "data_type": "date"},
                {"name": "year", "data_type": "int"},
                {"name": "quarter", "data_type": "int"},
                {"name": "month", "data_type": "int"},
                {"name": "month_name", "data_type": "varchar"},
                {"name": "day_of_week", "data_type": "int"},
                {"name": "day_name", "data_type": "varchar"},
                {"name": "is_weekend", "data_type": "boolean"},
            ],
        }

        # Timestamp vs business date handling
        if self.config.time.timestamp_business_date_relation.value == "different":
            dim["_warning"] = "Timestamps differ from business dates - you may need TWO date FKs!"
            scaffold.todos.append(ScaffoldTodo(
                location="dim_date",
                question="How will you track both event timestamp and business effective date?",
                hints=[
                    "Option 1: Two date dimension FKs (event_date_key, business_date_key)",
                    "Option 2: Store business_date in fact, join to dim_date for reporting",
                    "Consider which date matters for which queries",
                ],
                decision_type="temporal",
            ))

        scaffold.dimension_tables.append(dim)

    def _add_product_dimension(self, scaffold: ScaffoldedSchema) -> None:
        """Add product dimension scaffold."""
        hierarchy_freq = self.config.products.hierarchy_change_frequency

        # Intentionally questionable SCD choice
        scd_strategy = "type_1"  # WRONG for changing hierarchies

        dim: dict[str, Any] = {
            "name": "dim_product",
            "natural_key": ["sku"],
            "surrogate_key": "product_key",
            "scd_strategy": scd_strategy,
            "attributes": [
                {"name": "sku", "data_type": "varchar"},
                {"name": "product_name", "data_type": "varchar"},
                {"name": "category", "data_type": "varchar", "scd_tracked": False},
                {"name": "subcategory", "data_type": "varchar", "scd_tracked": False},
                {"name": "brand", "data_type": "varchar"},
                {"name": "unit_price_cents", "data_type": "int"},
            ],
        }

        # Add warnings for traps
        if hierarchy_freq != ProductHierarchyChangeFrequency.NONE:
            dim["_warning"] = f"Product hierarchy changes {hierarchy_freq.value} - Type 1 loses history!"
            dim["_todo_scd"] = "Consider Type 2 SCD for category/subcategory tracking"
            scaffold.todos.append(ScaffoldTodo(
                location="dim_product.scd_strategy",
                question=f"Product categories change {hierarchy_freq.value}. What SCD strategy?",
                hints=[
                    "Type 1: Overwrite (loses history)",
                    "Type 2: Add rows (preserves history, needs effective dates)",
                    "Consider marking category attributes as scd_tracked: true",
                ],
                decision_type="scd",
            ))

        if self.config.products.sku_reuse:
            dim["_warning_sku"] = "SKU codes are REUSED for different products over time!"
            scaffold.todos.append(ScaffoldTodo(
                location="dim_product.natural_key",
                question="SKUs are reused. Is SKU alone sufficient as natural key?",
                hints=[
                    "May need composite key: sku + effective_from_date",
                    "Or use surrogate key and track SKU history",
                    "Current setup will conflate different products with same SKU",
                ],
                decision_type="identity",
            ))

        scaffold.dimension_tables.append(dim)

    def _add_store_dimension(self, scaffold: ScaffoldedSchema) -> None:
        """Add store dimension scaffold."""
        dim: dict[str, Any] = {
            "name": "dim_store",
            "natural_key": ["store_id"],
            "surrogate_key": "store_key",
            "scd_strategy": "type_1",
            "attributes": [
                {"name": "store_id", "data_type": "varchar"},
                {"name": "store_name", "data_type": "varchar"},
                {"name": "channel", "data_type": "varchar"},  # physical, online
            ],
        }

        if self.config.stores.physical_stores:
            dim["attributes"].extend([
                {"name": "address", "data_type": "varchar"},
                {"name": "city", "data_type": "varchar"},
                {"name": "state", "data_type": "varchar"},
            ])

        if self.config.stores.store_lifecycle_changes:
            dim["_warning"] = "Stores open, close, and merge - Type 1 loses this history!"
            dim["attributes"].extend([
                {"name": "open_date", "data_type": "date"},
                {"name": "close_date", "data_type": "date", "_note": "nullable"},
            ])
            scaffold.todos.append(ScaffoldTodo(
                location="dim_store.scd_strategy",
                question="Stores have lifecycle changes. How to track store history?",
                hints=[
                    "Type 2 SCD to track openings, closings, merges",
                    "Store merges are particularly tricky",
                    "Consider how to attribute historical sales after a merge",
                ],
                decision_type="scd",
            ))

        scaffold.dimension_tables.append(dim)

    def _add_customer_dimension(self, scaffold: ScaffoldedSchema) -> None:
        """Add customer dimension scaffold if customers exist."""
        reliability = self.config.customers.customer_id_reliability

        if reliability == CustomerIdReliability.ABSENT:
            scaffold.warnings.append(
                "No customer IDs in this shop - customer dimension may not be needed"
            )
            return

        dim: dict[str, Any] = {
            "name": "dim_customer",
            "natural_key": ["customer_id"],
            "surrogate_key": "customer_key",
            "scd_strategy": "type_1",
            "attributes": [
                {"name": "customer_id", "data_type": "varchar"},
                {"name": "customer_type", "data_type": "varchar"},
            ],
        }

        if reliability == CustomerIdReliability.UNRELIABLE:
            dim["_warning"] = "Customer IDs are UNRELIABLE - may merge, split, or be duplicated!"
            scaffold.todos.append(ScaffoldTodo(
                location="dim_customer",
                question="Customer IDs are unreliable. How to handle identity issues?",
                hints=[
                    "Consider fuzzy matching / identity resolution",
                    "May need a customer_alias bridge table",
                    "Accept some data quality issues or clean upstream",
                ],
                decision_type="identity",
            ))

        if self.config.customers.anonymous_allowed:
            dim["_note_anonymous"] = "Anonymous customers allowed - handle NULL/unknown customer"
            dim["attributes"].append({"name": "is_anonymous", "data_type": "boolean"})

        if self.config.customers.household_grouping:
            dim["attributes"].append({
                "name": "household_id",
                "data_type": "varchar",
                "_todo": "Households can change - track history?",
            })
            scaffold.todos.append(ScaffoldTodo(
                location="dim_customer.household_id",
                question="Customers are grouped into households. How to model this?",
                hints=[
                    "Simple: household_id attribute in dim_customer",
                    "Complex: separate dim_household with relationship",
                    "Households can change over time - consider SCD",
                ],
                decision_type="relationship",
            ))

        scaffold.dimension_tables.append(dim)

    def _add_relationships(self, scaffold: ScaffoldedSchema) -> None:
        """Add relationships between facts and dimensions."""
        # Get fact and dimension names
        fact_names = [f["name"] for f in scaffold.fact_tables]
        dim_names = [d["name"] for d in scaffold.dimension_tables]

        for fact_name in fact_names:
            fact = next(f for f in scaffold.fact_tables if f["name"] == fact_name)
            dim_keys = fact.get("dimension_keys", [])

            for dim_key in dim_keys:
                # Derive dimension name from key
                dim_name = f"dim_{dim_key.replace('_key', '')}"

                if dim_name in dim_names:
                    scaffold.relationships.append({
                        "fact_table": fact_name,
                        "dimension_table": dim_name,
                        "fact_column": dim_key,
                        "dimension_column": dim_key,
                        "cardinality": "many-to-one",
                    })

        # Promotion many-to-many
        if self.config.promotions.promotions_per_line_item == PromotionsPerLineItem.MANY:
            scaffold.todos.append(ScaffoldTodo(
                location="relationships",
                question="Multiple promotions per line item - how to model?",
                hints=[
                    "Bridge table: bridge_sales_promotion",
                    "Separate promotion fact table",
                    "Array/JSON column (limited queryability)",
                ],
                decision_type="relationship",
            ))

    def _add_global_warnings(self, scaffold: ScaffoldedSchema) -> None:
        """Add global warnings based on configuration."""
        if self.config.transactions.voids_enabled:
            scaffold.warnings.append(
                "Voids are enabled - decide how to track or exclude voided transactions"
            )

        if self.config.transactions.manual_overrides:
            scaffold.warnings.append(
                "Manual price overrides allowed - original vs override price tracking?"
            )

        if self.config.promotions.post_transaction_promotions:
            scaffold.warnings.append(
                "Post-transaction promotions exist - adjustments after the fact!"
            )
