"""Actionable feedback models for schema evaluation."""

from dataclasses import dataclass, field
from enum import Enum

from dim_mod_sim.evaluator.result import Deduction, EvaluationResult, Severity


class ViolationType(str, Enum):
    """Categories of schema modeling violations."""

    GRAIN_VIOLATION = "grain_violation"
    TEMPORAL_LIE = "temporal_lie"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    OVER_MODELING = "over_modeling"
    UNDER_MODELING = "under_modeling"
    DATA_LOSS = "data_loss"
    FAN_OUT_RISK = "fan_out_risk"


# Map axis names to default violation types
AXIS_TO_VIOLATION_TYPE: dict[str, ViolationType] = {
    "grain_correctness": ViolationType.GRAIN_VIOLATION,
    "temporal_correctness": ViolationType.TEMPORAL_LIE,
    "semantic_faithfulness": ViolationType.SEMANTIC_MISMATCH,
    "structural_optimality": ViolationType.OVER_MODELING,
    "event_preservation": ViolationType.DATA_LOSS,
    "queryability": ViolationType.UNDER_MODELING,
}


@dataclass
class ConcreteViolation:
    """A specific, explainable violation with actionable details."""

    violation_type: ViolationType
    what_went_wrong: str
    concrete_example: str
    consequence: str
    fix_hint: str
    affected_tables: list[str]
    severity: Severity
    points_deducted: int

    @classmethod
    def from_deduction(
        cls,
        deduction: Deduction,
        axis_name: str,
    ) -> "ConcreteViolation":
        """Create a ConcreteViolation from an existing Deduction."""
        # Use extended fields if present, otherwise generate defaults
        violation_type = (
            deduction.violation_type
            if deduction.violation_type
            else AXIS_TO_VIOLATION_TYPE.get(axis_name, ViolationType.SEMANTIC_MISMATCH)
        )

        return cls(
            violation_type=violation_type,
            what_went_wrong=deduction.reason,
            concrete_example=deduction.concrete_example or _generate_example(deduction, axis_name),
            consequence=deduction.consequence or _generate_consequence(deduction, axis_name),
            fix_hint=deduction.fix_hint or _generate_fix_hint(deduction, axis_name),
            affected_tables=deduction.affected_elements,
            severity=deduction.severity,
            points_deducted=deduction.points,
        )


@dataclass
class ActionableFeedback:
    """Complete actionable feedback for an evaluation result."""

    total_score: int
    max_score: int
    percentage: float
    violations: list[ConcreteViolation] = field(default_factory=list)
    by_category: dict[ViolationType, list[ConcreteViolation]] = field(default_factory=dict)
    fix_priority: list[str] = field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_result(cls, result: EvaluationResult) -> "ActionableFeedback":
        """Create ActionableFeedback from an EvaluationResult."""
        violations: list[ConcreteViolation] = []
        by_category: dict[ViolationType, list[ConcreteViolation]] = {}

        # Collect all violations from all axes
        for axis_name, axis_score in result.axis_scores.items():
            for deduction in axis_score.deductions:
                violation = ConcreteViolation.from_deduction(deduction, axis_name)
                violations.append(violation)

                if violation.violation_type not in by_category:
                    by_category[violation.violation_type] = []
                by_category[violation.violation_type].append(violation)

        # Sort violations by severity and points
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.MAJOR: 1,
            Severity.MODERATE: 2,
            Severity.MINOR: 3,
        }
        violations.sort(key=lambda v: (severity_order[v.severity], -v.points_deducted))

        # Generate fix priority
        fix_priority = _generate_fix_priority(violations)

        # Generate summary
        summary = _generate_summary(by_category)

        return cls(
            total_score=result.total_score,
            max_score=result.max_possible_score,
            percentage=result.percentage,
            violations=violations,
            by_category=by_category,
            fix_priority=fix_priority,
            summary=summary,
        )


def _generate_example(deduction: Deduction, axis_name: str) -> str:
    """Generate a concrete example based on the deduction."""
    reason = deduction.reason.lower()

    if "grain" in reason or axis_name == "grain_correctness":
        if "mixed" in reason:
            return "Transaction TXN-001 has line items; TXN-002 is receipt-level only"
        if "many-to-many" in reason:
            return "Customer C-100 applies 3 promotions; all 3 rows appear in query output"
        return "The fact table grain is ambiguous for certain events"

    if "scd" in reason or "history" in reason or axis_name == "temporal_correctness":
        return "SKU-123 was in 'Electronics' in January, moved to 'Clearance' in February"

    if "return" in reason:
        return "Return RET-500 has no original_transaction_id - cannot trace to sale"

    if "payment" in reason:
        return "Transaction TXN-200 split across cash and credit card"

    if "customer" in reason or "anonymous" in reason:
        return "15% of transactions have null or unreliable customer identifiers"

    return ""


def _generate_consequence(deduction: Deduction, axis_name: str) -> str:
    """Generate consequence description based on the deduction."""
    reason = deduction.reason.lower()

    if "grain" in reason or axis_name == "grain_correctness":
        if "mixed" in reason:
            return "SUM(quantity) will double-count or lose items. Aggregate queries are unreliable."
        if "many-to-many" in reason:
            return "Joining without a bridge table causes fan-out, inflating all measures."
        return "Queries may produce inconsistent or incorrect aggregations"

    if "scd" in reason or "history" in reason or axis_name == "temporal_correctness":
        return "Historical reports show current values, not point-in-time truth"

    if "return" in reason:
        return "Cannot calculate true customer lifetime value or accurate refund rates"

    if "payment" in reason:
        return "Cannot analyze payment method trends or reconcile transactions accurately"

    if "missing" in reason or "no " in reason:
        return "Business requirement cannot be answered by this model"

    return "Query results will be incorrect or incomplete for some business questions"


def _generate_fix_hint(deduction: Deduction, axis_name: str) -> str:
    """Generate fix hint based on the deduction."""
    reason = deduction.reason.lower()

    if "grain" in reason or axis_name == "grain_correctness":
        if "mixed" in reason:
            return "Split into separate fact tables per grain, or add is_aggregated indicator"
        if "many-to-many" in reason:
            return "Add a bridge table to handle the many-to-many relationship"
        if "description" in reason:
            return "Add a clear grain_description stating exactly what one row represents"
        return "Clarify the grain and ensure all grain columns are properly defined"

    if "scd" in reason or "type_1" in reason or axis_name == "temporal_correctness":
        return "Change to Type 2 SCD and mark changing attributes with scd_tracked: true"

    if "return" in reason:
        if "reference" in reason:
            return "Add nullable original_transaction_id FK, or model orphan returns separately"
        return "Add a returns fact table to capture return events"

    if "payment" in reason:
        return "Add a payments fact table or payment bridge table for multiple payments"

    if "customer" in reason:
        if "no customer" in reason or "missing" in reason:
            return "Add a customer dimension with proper handling of anonymous customers"
        return "Review customer dimension design for this shop's ID reliability"

    if "inventory" in reason:
        return "Add an inventory fact table matching the shop's tracking method"

    return "Review the schema against shop configuration requirements"


def _generate_fix_priority(violations: list[ConcreteViolation]) -> list[str]:
    """Generate prioritized list of fixes."""
    priority: list[str] = []
    seen_types: set[ViolationType] = set()

    for v in violations:
        if v.violation_type in seen_types:
            continue
        seen_types.add(v.violation_type)

        if v.severity == Severity.CRITICAL:
            impact = "(breaks queries)"
        elif v.severity == Severity.MAJOR:
            impact = "(significant data issues)"
        else:
            impact = ""

        tables = ", ".join(v.affected_tables[:2]) if v.affected_tables else "schema"
        priority.append(f"{v.fix_hint} [{tables}] {impact}".strip())

        if len(priority) >= 5:
            break

    return priority


def _generate_summary(by_category: dict[ViolationType, list[ConcreteViolation]]) -> str:
    """Generate a summary line for the feedback."""
    parts = []
    type_labels = {
        ViolationType.GRAIN_VIOLATION: "grain violations",
        ViolationType.TEMPORAL_LIE: "temporal lies",
        ViolationType.SEMANTIC_MISMATCH: "semantic mismatches",
        ViolationType.OVER_MODELING: "over-modeling issues",
        ViolationType.UNDER_MODELING: "under-modeling issues",
        ViolationType.DATA_LOSS: "data loss risks",
        ViolationType.FAN_OUT_RISK: "fan-out risks",
    }

    for vtype, violations in by_category.items():
        if violations:
            parts.append(f"{len(violations)} {type_labels.get(vtype, vtype.value)}")

    return " | ".join(parts) if parts else "No violations found"
