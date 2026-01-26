"""Base class for evaluation axes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from dim_mod_sim.events.models import EventLog, EventType
from dim_mod_sim.evaluator.result import AxisScore
from dim_mod_sim.schema.models import SchemaSubmission
from dim_mod_sim.shop.config import ShopConfiguration
from dim_mod_sim.shop.options import (
    InventoryType,
    ProductHierarchyChangeFrequency,
    ReturnsReferencePolicy,
)


@dataclass
class EvaluationContext:
    """Context containing all information needed for evaluation."""

    config: ShopConfiguration
    events: EventLog

    # Derived requirements (computed once)
    required_event_types: set[EventType] = field(default_factory=set)
    dimensions_requiring_scd: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Compute derived requirements."""
        self._compute_required_event_types()
        self._compute_scd_requirements()

    def _compute_required_event_types(self) -> None:
        """Determine which event types must be supported."""
        self.required_event_types = {EventType.SALE}

        if self.config.returns.reference_policy != ReturnsReferencePolicy.NEVER:
            self.required_event_types.add(EventType.RETURN)

        if self.config.transactions.voids_enabled:
            self.required_event_types.add(EventType.VOID)

        if self.config.time.backdated_corrections:
            self.required_event_types.add(EventType.CORRECTION)

        if self.config.inventory.tracked:
            inv_type = self.config.inventory.inventory_type
            if inv_type in (InventoryType.TRANSACTIONAL, InventoryType.BOTH):
                self.required_event_types.add(EventType.INVENTORY_ADJUSTMENT)
            if inv_type in (InventoryType.PERIODIC_SNAPSHOT, InventoryType.BOTH):
                self.required_event_types.add(EventType.INVENTORY_SNAPSHOT)

        if self.config.products.hierarchy_change_frequency != ProductHierarchyChangeFrequency.NONE:
            self.required_event_types.add(EventType.PRODUCT_CHANGE)

        if self.config.stores.store_lifecycle_changes:
            self.required_event_types.add(EventType.STORE_CHANGE)

    def _compute_scd_requirements(self) -> None:
        """Determine which dimensions need SCD handling."""
        # Product dimension needs SCD if hierarchy changes or prices change
        if self.config.products.hierarchy_change_frequency != ProductHierarchyChangeFrequency.NONE:
            self.dimensions_requiring_scd.add("product")

        # Store dimension needs SCD if lifecycle changes
        if self.config.stores.store_lifecycle_changes:
            self.dimensions_requiring_scd.add("store")

        # Customer dimension needs SCD if household grouping can change
        if self.config.customers.household_grouping:
            self.dimensions_requiring_scd.add("customer")

    def requires_scd(self, dimension_name: str) -> bool:
        """Check if a dimension requires SCD tracking."""
        # Normalize dimension name
        name_lower = dimension_name.lower()
        for dim in self.dimensions_requiring_scd:
            if dim in name_lower:
                return True
        return False


class EvaluationAxis(ABC):
    """Base class for evaluation axes."""

    name: str = "base"
    max_score: int = 100

    def __init__(self, context: EvaluationContext) -> None:
        self.context = context

    @abstractmethod
    def evaluate(self, submission: SchemaSubmission) -> AxisScore:
        """Evaluate the submission and return a score."""
        pass

    def _generate_commentary(self, deductions: list) -> str:
        """Generate commentary based on deductions."""
        if not deductions:
            return "No issues found."

        critical = [d for d in deductions if d.severity.value == "critical"]
        major = [d for d in deductions if d.severity.value == "major"]

        if critical:
            return f"Critical issues found: {len(critical)} critical, {len(major)} major problems."
        elif major:
            return f"Significant issues found: {len(major)} major problems."
        else:
            return f"Minor issues found: {len(deductions)} total."
