"""Scenario generators for explaining schema problems."""

from dim_mod_sim.evaluator.result import EvaluationResult, Severity
from dim_mod_sim.explain.models import QueryScenario
from dim_mod_sim.schema.models import SCDType, SchemaSubmission
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import (
    ProductHierarchyChangeFrequency,
    ReturnsReferencePolicy,
    ReturnsPricingPolicy,
    TimestampBusinessDateRelation,
    TransactionGrain,
)


def generate_grain_scenarios(
    config: ShopConfiguration,
    schema: SchemaSubmission,
    result: EvaluationResult,
) -> list[QueryScenario]:
    """Generate scenarios that demonstrate grain problems."""
    scenarios: list[QueryScenario] = []

    # Mixed grain scenario
    if config.transactions.grain == TransactionGrain.MIXED:
        # Check if schema has mixed grain issues
        has_mixed_grain_fact = any(
            "mixed" in ft.grain_description.lower() or "or" in ft.grain_description.lower()
            for ft in schema.fact_tables
        )

        if has_mixed_grain_fact:
            scenarios.append(QueryScenario(
                scenario_name="The Mixed Grain Trap",
                business_question="How many items did we sell last Tuesday?",
                setup_description=(
                    "Transaction TXN-001 has 3 line items (items A, B, C).\n"
                    "Transaction TXN-002 is receipt-level only (total: 5 items, no breakdown)."
                ),
                expected_answer="8 items (3 + 5)",
                actual_with_schema=(
                    "Either 2 items (counting rows), or 8 items (if you sum quantity), "
                    "but the grain inconsistency makes this query unreliable."
                ),
                why_wrong=(
                    "The fact table mixes line-item rows with receipt-level rows. "
                    "COUNT(*) counts rows, not items. SUM(quantity) might work "
                    "if all rows have quantity, but the semantic meaning differs."
                ),
                root_cause="Fact table has mixed grain without clear delineation",
                events_involved=["TXN-001 (3 lines)", "TXN-002 (receipt only)"],
                severity="critical",
            ))

    # Multiple payments fan-out
    if config.transactions.multiple_payments:
        # Check if there's no bridge table for payments
        has_payment_bridge = any(
            "payment" in bt.name.lower() for bt in schema.bridge_tables
        )
        has_payment_fact = any(
            "payment" in ft.name.lower() for ft in schema.fact_tables
        )

        if not has_payment_bridge and not has_payment_fact:
            scenarios.append(QueryScenario(
                scenario_name="The Payment Fan-Out",
                business_question="What was total revenue last week?",
                setup_description=(
                    "Transaction TXN-100 is for $100, paid $60 cash + $40 credit.\n"
                    "Transaction TXN-101 is for $50, paid entirely by gift card."
                ),
                expected_answer="$150 total revenue",
                actual_with_schema=(
                    "If payments are modeled as dimension rows joined to facts, "
                    "TXN-100 appears twice (once per payment method), "
                    "giving $200 ($100 + $100 + $50) or worse."
                ),
                why_wrong=(
                    "Without proper payment modeling, joining to payment data "
                    "causes fan-out, duplicating the transaction amounts."
                ),
                root_cause="No bridge table or separate fact for multiple payments",
                events_involved=["TXN-100 ($60 + $40)", "TXN-101 ($50)"],
                severity="major",
            ))

    return scenarios


def generate_temporal_scenarios(
    config: ShopConfiguration,
    schema: SchemaSubmission,
    result: EvaluationResult,
) -> list[QueryScenario]:
    """Generate scenarios that demonstrate temporal problems."""
    scenarios: list[QueryScenario] = []

    # Backdated corrections
    if config.time.backdated_corrections:
        # Check if schema distinguishes event time from business date
        has_dual_dates = False
        for ft in schema.fact_tables:
            cols = [gc.name.lower() for gc in ft.grain_columns]
            cols += [dk.lower() for dk in ft.dimension_keys]
            if ("event" in " ".join(cols) or "record" in " ".join(cols)) and "business" in " ".join(cols):
                has_dual_dates = True

        if not has_dual_dates:
            scenarios.append(QueryScenario(
                scenario_name="The Backdated Correction",
                business_question="What were total sales on January 15th?",
                setup_description=(
                    "TXN-500 was recorded on Jan 15 for $100.\n"
                    "On Jan 20, a manager corrected TXN-500's amount to $150.\n"
                    "The correction is backdated to be effective Jan 15."
                ),
                expected_answer="$150 (the corrected amount)",
                actual_with_schema=(
                    "Either $100 (original), $150 (if overwritten), or $250 "
                    "(if both records exist without clear business date)."
                ),
                why_wrong=(
                    "The schema doesn't distinguish between event timestamp "
                    "(when recorded) and business effective date (when it applies). "
                    "This makes it impossible to correctly report Jan 15 sales."
                ),
                root_cause="No business_effective_date column separate from event_timestamp",
                events_involved=["TXN-500 original ($100)", "CORR-987 ($150, effective Jan 15)"],
                severity="major",
            ))

    # SCD for changing hierarchies
    if config.products.hierarchy_change_frequency != ProductHierarchyChangeFrequency.NONE:
        # Check product dimension SCD type
        product_dim = next(
            (d for d in schema.dimension_tables if "product" in d.name.lower()),
            None
        )

        if product_dim and product_dim.scd_strategy in (SCDType.TYPE_1, SCDType.NONE, SCDType.TYPE_0):
            scenarios.append(QueryScenario(
                scenario_name="The Rewritten History",
                business_question="What were sales by product category in Q1?",
                setup_description=(
                    "Product SKU-123 was in 'Electronics' for January and February.\n"
                    "In March, SKU-123 was moved to 'Clearance' category.\n"
                    "SKU-123 had $10,000 in Q1 sales."
                ),
                expected_answer="$10,000 in Electronics (where it was when sold)",
                actual_with_schema=(
                    "$10,000 shows as 'Clearance' because Type 1 SCD overwrote "
                    "the category. Historical category assignment is lost."
                ),
                why_wrong=(
                    "Type 1 SCD overwrites attributes without preserving history. "
                    "All historical sales now show current category values, "
                    "making historical category analysis impossible."
                ),
                root_cause=f"dim_product uses {product_dim.scd_strategy.value} instead of Type 2",
                events_involved=["SKU-123 sales in Jan/Feb", "Category change in March"],
                severity="major",
            ))

    # Timestamp vs business date
    if config.time.timestamp_business_date_relation == TimestampBusinessDateRelation.DIFFERENT:
        scenarios.append(QueryScenario(
            scenario_name="The Midnight Sale",
            business_question="What were sales for Monday vs Tuesday?",
            setup_description=(
                "Transaction at 11:55 PM Monday is recorded in the system.\n"
                "Due to overnight processing, the event timestamp is 12:05 AM Tuesday.\n"
                "The business considers this a Monday sale."
            ),
            expected_answer="Sale counts toward Monday",
            actual_with_schema=(
                "If using event timestamp for the date dimension, "
                "this sale appears on Tuesday's report."
            ),
            why_wrong=(
                "The business date (Monday) differs from the system timestamp (Tuesday). "
                "Without explicit business date tracking, date-based reports are wrong "
                "for all late-night transactions."
            ),
            root_cause="Schema uses timestamp instead of business effective date",
            events_involved=["Late-night transaction crossing midnight"],
            severity="moderate",
        ))

    return scenarios


def generate_semantic_scenarios(
    config: ShopConfiguration,
    schema: SchemaSubmission,
    result: EvaluationResult,
) -> list[QueryScenario]:
    """Generate scenarios that demonstrate semantic mismatches."""
    scenarios: list[QueryScenario] = []

    # Returns without original reference
    if config.returns.reference_policy == ReturnsReferencePolicy.SOMETIMES:
        return_fact = next(
            (ft for ft in schema.fact_tables if "return" in ft.name.lower()),
            None
        )

        if return_fact:
            has_optional_ref = any(
                "original" in gc.name.lower() or "nullable" in str(gc)
                for gc in return_fact.grain_columns
            )

            if not has_optional_ref:
                scenarios.append(QueryScenario(
                    scenario_name="The Orphan Return",
                    business_question="What is customer C-100's lifetime value?",
                    setup_description=(
                        "Customer C-100 made purchases totaling $500.\n"
                        "C-100 returned a $50 item without a receipt (allowed by policy).\n"
                        "The return has no original_transaction_id."
                    ),
                    expected_answer="$450 ($500 purchases - $50 return)",
                    actual_with_schema=(
                        "Either $500 (return not linked to customer) or error "
                        "(if original_transaction_id is required but NULL)."
                    ),
                    why_wrong=(
                        "Returns without receipts can't be linked to original transactions. "
                        "If the schema requires this link, orphan returns are dropped. "
                        "If it's missing, returns can't be attributed to customers."
                    ),
                    root_cause="Return fact doesn't handle NULL original_transaction_id",
                    events_involved=["C-100 purchases ($500)", "Orphan return ($50)"],
                    severity="major",
                ))

    # Arbitrary return pricing
    if config.returns.pricing_policy == ReturnsPricingPolicy.ARBITRARY_OVERRIDE:
        scenarios.append(QueryScenario(
            scenario_name="The Mystery Refund",
            business_question="What's our refund rate as a percentage of sales?",
            setup_description=(
                "Product sold for $100.\n"
                "Customer returns it, but manager overrides refund to $120 "
                "(goodwill gesture due to inconvenience)."
            ),
            expected_answer="Depends on business definition - $100 or $120?",
            actual_with_schema=(
                "If schema only stores refund amount, you get 120% refund rate. "
                "If it only stores original price, you miss the actual cash out."
            ),
            why_wrong=(
                "The shop allows arbitrary price overrides on returns. "
                "Without tracking both original and refund amounts, "
                "financial reconciliation is impossible."
            ),
            root_cause="Schema doesn't capture both original_price and actual_refund",
            events_involved=["Sale ($100)", "Return ($120 override)"],
            severity="moderate",
        ))

    return scenarios


def generate_all_scenarios(
    config: ShopConfiguration,
    schema: SchemaSubmission,
    result: EvaluationResult,
) -> list[QueryScenario]:
    """Generate all applicable scenarios based on config and schema issues."""
    scenarios: list[QueryScenario] = []

    scenarios.extend(generate_grain_scenarios(config, schema, result))
    scenarios.extend(generate_temporal_scenarios(config, schema, result))
    scenarios.extend(generate_semantic_scenarios(config, schema, result))

    # Sort by severity
    severity_order = {"critical": 0, "major": 1, "moderate": 2, "minor": 3}
    scenarios.sort(key=lambda s: severity_order.get(s.severity, 99))

    return scenarios
