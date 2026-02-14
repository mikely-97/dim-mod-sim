"""Event preservation evaluation axis."""

from dim_mod_sim.events.models import EventType
from dim_mod_sim.evaluator.axes.base import EvaluationAxis
from dim_mod_sim.evaluator.feedback import ViolationType
from dim_mod_sim.evaluator.result import AxisScore, Deduction, Severity
from dim_mod_sim.schema.models import SchemaSubmission
from dim_mod_sim.shop.options import TransactionGrain


class EventPreservationAxis(EvaluationAxis):
    """Evaluates whether all events can be represented without loss."""

    name = "event_preservation"
    max_score = 100

    def evaluate(self, submission: SchemaSubmission) -> AxisScore:
        """Evaluate event preservation."""
        deductions: list[Deduction] = []

        # Check 1: Can each event type be stored?
        deductions.extend(self._check_event_type_coverage(submission))

        # Check 2: Are all required fields capturable?
        deductions.extend(self._check_field_coverage(submission))

        # Check 3: Is grain fine enough to avoid forced aggregation?
        deductions.extend(self._check_grain_sufficiency(submission))

        score = max(0, self.max_score - sum(d.points for d in deductions))

        return AxisScore(
            axis_name=self.name,
            score=score,
            max_score=self.max_score,
            deductions=deductions,
            commentary=self._generate_commentary(deductions),
        )

    def _check_event_type_coverage(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check if all required event types have a home in a fact table."""
        deductions = []

        # Map event types to expected fact table patterns
        event_type_patterns = {
            EventType.SALE: ["sale", "transaction", "order"],
            EventType.RETURN: ["return", "refund"],
            EventType.VOID: ["void", "cancel", "transaction"],
            EventType.CORRECTION: ["correction", "adjustment", "transaction"],
            EventType.INVENTORY_ADJUSTMENT: ["inventory", "stock"],
            EventType.INVENTORY_SNAPSHOT: ["inventory", "stock", "snapshot"],
            EventType.PRODUCT_CHANGE: ["product"],
            EventType.STORE_CHANGE: ["store", "location"],
        }

        fact_names_lower = [ft.name.lower() for ft in submission.fact_tables]

        for event_type in self.context.required_event_types:
            patterns = event_type_patterns.get(event_type, [])
            found = False

            for pattern in patterns:
                if any(pattern in name for name in fact_names_lower):
                    found = True
                    break

            if not found:
                deductions.append(Deduction(
                    points=20,
                    reason=f"No fact table appears to support {event_type.value} events",
                    severity=Severity.CRITICAL,
                    affected_elements=[event_type.value],
                    violation_type=ViolationType.DATA_LOSS,
                    concrete_example=f"{event_type.value} events from the shop cannot be stored anywhere",
                    consequence=f"All {event_type.value} data is lost; related business questions cannot be answered",
                    fix_hint=f"Add a fact table to capture {event_type.value} events",
                ))

        return deductions

    def _check_field_coverage(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check if essential fields can be stored."""
        deductions = []

        # Check for essential sale fields
        sale_facts = [
            ft for ft in submission.fact_tables
            if any(p in ft.name.lower() for p in ["sale", "transaction", "order"])
        ]

        if sale_facts:
            sale_fact = sale_facts[0]
            all_columns = (
                [gc.name.lower() for gc in sale_fact.grain_columns]
                + [m.name.lower() for m in sale_fact.measures]
                + [dk.lower() for dk in sale_fact.dimension_keys]
            )

            # Check for quantity
            if not any("quantity" in col or "qty" in col for col in all_columns):
                if self.context.config.transactions.grain != TransactionGrain.RECEIPT_LEVEL:
                    deductions.append(Deduction(
                        points=10,
                        reason="Sales fact appears to lack quantity measure for line items",
                        severity=Severity.MODERATE,
                        affected_elements=[sale_fact.name],
                    ))

            # Check for payment tracking if multiple payments enabled
            if self.context.config.transactions.multiple_payments:
                has_payment_dim = any(
                    "payment" in r.dimension_table.lower()
                    for r in submission.get_relationships_for_fact(sale_fact.name)
                )
                if not has_payment_dim:
                    # Check for separate payment fact
                    payment_facts = [
                        ft for ft in submission.fact_tables
                        if "payment" in ft.name.lower()
                    ]
                    if not payment_facts:
                        deductions.append(Deduction(
                            points=15,
                            reason="Multiple payments supported but no payment dimension or fact found",
                            severity=Severity.MAJOR,
                            affected_elements=[sale_fact.name],
                        ))

        return deductions

    def _check_grain_sufficiency(self, submission: SchemaSubmission) -> list[Deduction]:
        """Check if fact grain is fine enough."""
        deductions = []

        grain = self.context.config.transactions.grain

        if grain == TransactionGrain.LINE_ITEM_LEVEL:
            # Must have line-item grain fact
            line_facts = [
                ft for ft in submission.fact_tables
                if any(
                    p in ft.grain_description.lower()
                    for p in ["line item", "line-item", "lineitem", "item"]
                )
            ]
            if not line_facts:
                deductions.append(Deduction(
                    points=25,
                    reason="Shop uses line-item grain but no line-item level fact table found",
                    severity=Severity.CRITICAL,
                    affected_elements=["grain"],
                    violation_type=ViolationType.DATA_LOSS,
                    concrete_example="Transaction with 5 line items becomes 1 row; individual item data is lost",
                    consequence="Cannot analyze product-level sales, basket composition, or item-level returns",
                    fix_hint="Add a line-item grain fact table with line_number in the grain",
                ))

        elif grain == TransactionGrain.MIXED:
            # Should have both or a flexible structure
            line_facts = [
                ft for ft in submission.fact_tables
                if any(
                    p in ft.grain_description.lower()
                    for p in ["line item", "line-item", "lineitem", "item"]
                )
            ]
            if not line_facts:
                deductions.append(Deduction(
                    points=15,
                    reason="Shop uses mixed grain; consider supporting line-item detail when available",
                    severity=Severity.MODERATE,
                    affected_elements=["grain"],
                ))

        return deductions
