"""Semantic faithfulness evaluation axis."""

from dim_mod_sim.evaluator.axes.base import EvaluationAxis
from dim_mod_sim.evaluator.feedback import ViolationType
from dim_mod_sim.evaluator.result import AxisScore, Deduction, Severity
from dim_mod_sim.schema.models import SchemaSubmission
from dim_mod_sim.shop.options import (
    CustomerIdReliability,
    PromotionsPerLineItem,
    ReturnsReferencePolicy,
    TransactionGrain,
)


class SemanticFaithfulnessAxis(EvaluationAxis):
    """Evaluates whether the model reflects shop rules accurately."""

    name = "semantic_faithfulness"
    max_score = 100

    def evaluate(self, submission: SchemaSubmission) -> AxisScore:
        """Evaluate semantic faithfulness."""
        deductions: list[Deduction] = []

        # Check various business rules are properly modeled
        deductions.extend(self._check_transaction_modeling(submission))
        deductions.extend(self._check_customer_modeling(submission))
        deductions.extend(self._check_promotion_modeling(submission))
        deductions.extend(self._check_returns_modeling(submission))
        deductions.extend(self._check_inventory_modeling(submission))

        score = max(0, self.max_score - sum(d.points for d in deductions))

        return AxisScore(
            axis_name=self.name,
            score=score,
            max_score=self.max_score,
            deductions=deductions,
            commentary=self._generate_commentary(deductions),
        )

    def _check_transaction_modeling(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check transaction-related rules are modeled correctly."""
        deductions = []
        cfg = self.context.config.transactions

        # Multiple payments
        if cfg.multiple_payments:
            has_payment_structure = any(
                "payment" in ft.name.lower() for ft in submission.fact_tables
            ) or any(
                "payment" in dt.name.lower() for dt in submission.dimension_tables
            )

            if not has_payment_structure:
                deductions.append(Deduction(
                    points=15,
                    reason="Multiple payments are supported but no payment-specific modeling found",
                    severity=Severity.MAJOR,
                    affected_elements=["payment"],
                    violation_type=ViolationType.SEMANTIC_MISMATCH,
                    concrete_example="Transaction paid $50 cash + $75 credit card, but model only stores one payment",
                    consequence="Cannot analyze payment method mix, reconcile transactions, or track tender types",
                    fix_hint="Add a payment fact table or payment bridge table for many-to-one payments",
                ))

        # Voids
        if cfg.voids_enabled:
            void_support = any(
                "void" in ft.name.lower() or "status" in ft.grain_description.lower()
                for ft in submission.fact_tables
            )

            if not void_support:
                deductions.append(Deduction(
                    points=10,
                    reason="Voids are supported but no void tracking mechanism found",
                    severity=Severity.MODERATE,
                    affected_elements=["void"],
                ))

        return deductions

    def _check_customer_modeling(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check customer-related rules are modeled correctly."""
        deductions = []
        cfg = self.context.config.customers

        customer_dims = [
            dt for dt in submission.dimension_tables
            if "customer" in dt.name.lower()
        ]

        if cfg.customer_id_reliability == CustomerIdReliability.ABSENT:
            if customer_dims:
                deductions.append(Deduction(
                    points=5,
                    reason="Customer dimension exists but shop has no customer IDs",
                    severity=Severity.MINOR,
                    affected_elements=[d.name for d in customer_dims],
                ))
        else:
            if not customer_dims:
                deductions.append(Deduction(
                    points=15,
                    reason="Shop has customer IDs but no customer dimension found",
                    severity=Severity.MAJOR,
                    affected_elements=["customer"],
                ))

            # Household grouping
            if cfg.household_grouping and customer_dims:
                household_attr = any(
                    "household" in attr.name.lower()
                    for dim in customer_dims
                    for attr in dim.attributes
                )
                household_dim = any(
                    "household" in dt.name.lower()
                    for dt in submission.dimension_tables
                )

                if not household_attr and not household_dim:
                    deductions.append(Deduction(
                        points=10,
                        reason="Household grouping is used but not modeled",
                        severity=Severity.MODERATE,
                        affected_elements=["household"],
                    ))

        return deductions

    def _check_promotion_modeling(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check promotion-related rules are modeled correctly."""
        deductions = []
        cfg = self.context.config.promotions

        promo_dims = [
            dt for dt in submission.dimension_tables
            if "promo" in dt.name.lower() or "discount" in dt.name.lower()
        ]

        # Multiple promotions per line item
        if cfg.promotions_per_line_item == PromotionsPerLineItem.MANY:
            # Should have bridge table or promotion fact
            promo_bridge = any(
                "promo" in bt.name.lower()
                for bt in submission.bridge_tables
            )
            promo_fact = any(
                "promo" in ft.name.lower()
                for ft in submission.fact_tables
            )

            if not promo_bridge and not promo_fact:
                deductions.append(Deduction(
                    points=15,
                    reason="Multiple promotions per line item but no bridge/fact to support many-to-many",
                    severity=Severity.MAJOR,
                    affected_elements=["promotion"],
                ))

        # Basket-level promotions
        if cfg.basket_level_promotions:
            basket_support = any(
                "basket" in ft.name.lower() or "order" in ft.name.lower()
                for ft in submission.fact_tables
            )
            if not basket_support and not promo_dims:
                deductions.append(Deduction(
                    points=10,
                    reason="Basket-level promotions exist but may not be properly modeled",
                    severity=Severity.MODERATE,
                    affected_elements=["basket_promotion"],
                ))

        return deductions

    def _check_returns_modeling(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check returns-related rules are modeled correctly."""
        deductions = []
        cfg = self.context.config.returns

        if cfg.reference_policy != ReturnsReferencePolicy.NEVER:
            return_facts = [
                ft for ft in submission.fact_tables
                if "return" in ft.name.lower() or "refund" in ft.name.lower()
            ]

            if not return_facts:
                deductions.append(Deduction(
                    points=15,
                    reason="Returns are supported but no return fact table found",
                    severity=Severity.MAJOR,
                    affected_elements=["returns"],
                    violation_type=ViolationType.UNDER_MODELING,
                    concrete_example="Customer returns item for $50 refund - nowhere to record this event",
                    consequence="Return rates, refund amounts, and customer satisfaction metrics unavailable",
                    fix_hint="Add a returns fact table to capture return events and reasons",
                ))

            # Check for original transaction reference
            if cfg.reference_policy == ReturnsReferencePolicy.ALWAYS:
                for rf in return_facts:
                    has_orig_ref = any(
                        "original" in gc.name.lower() or "orig" in gc.name.lower()
                        for gc in rf.grain_columns
                    ) or any(
                        "original" in dk.lower() or "orig" in dk.lower()
                        for dk in rf.dimension_keys
                    )

                    if not has_orig_ref:
                        deductions.append(Deduction(
                            points=10,
                            reason=f"Return fact '{rf.name}' should reference original transaction",
                            severity=Severity.MODERATE,
                            affected_elements=[rf.name],
                        ))

        return deductions

    def _check_inventory_modeling(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check inventory-related rules are modeled correctly."""
        deductions = []
        cfg = self.context.config.inventory

        if cfg.tracked:
            inv_facts = [
                ft for ft in submission.fact_tables
                if "inventory" in ft.name.lower() or "stock" in ft.name.lower()
            ]

            if not inv_facts:
                deductions.append(Deduction(
                    points=15,
                    reason="Inventory is tracked but no inventory fact table found",
                    severity=Severity.MAJOR,
                    affected_elements=["inventory"],
                ))

        return deductions
