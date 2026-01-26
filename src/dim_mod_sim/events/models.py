"""Event data models."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Types of events that can be generated."""

    SALE = "sale"
    RETURN = "return"
    VOID = "void"
    CORRECTION = "correction"
    INVENTORY_ADJUSTMENT = "inventory_adjustment"
    INVENTORY_SNAPSHOT = "inventory_snapshot"
    PRODUCT_CHANGE = "product_change"
    STORE_CHANGE = "store_change"


@dataclass(frozen=True)
class LineItem:
    """A line item within a transaction."""

    line_number: int
    sku: str
    quantity: int
    unit_price_cents: int
    discount_cents: int = 0
    promotion_codes: tuple[str, ...] = ()
    bundle_parent_line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "line_number": self.line_number,
            "sku": self.sku,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "discount_cents": self.discount_cents,
            "promotion_codes": list(self.promotion_codes),
            "bundle_parent_line": self.bundle_parent_line,
        }


@dataclass(frozen=True)
class Payment:
    """A payment within a transaction."""

    payment_method: str
    amount_cents: int
    reference_number: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "payment_method": self.payment_method,
            "amount_cents": self.amount_cents,
            "reference_number": self.reference_number,
        }


@dataclass(frozen=True)
class BaseEvent:
    """Base class for all events with common fields."""

    event_id: str
    event_type: EventType
    event_timestamp: datetime
    business_effective_date: date

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "event_timestamp": self.event_timestamp.isoformat(),
            "business_effective_date": self.business_effective_date.isoformat(),
        }


@dataclass(frozen=True)
class SaleEvent(BaseEvent):
    """A sale transaction event."""

    transaction_id: str
    store_id: str
    register_id: str
    employee_id: str
    line_items: tuple[LineItem, ...]
    payments: tuple[Payment, ...]
    customer_id: str | None = None
    is_aggregated: bool = False  # True for receipt-level grain

    def __post_init__(self) -> None:
        # Ensure event_type is set correctly
        object.__setattr__(self, "event_type", EventType.SALE)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "transaction_id": self.transaction_id,
            "store_id": self.store_id,
            "register_id": self.register_id,
            "employee_id": self.employee_id,
            "customer_id": self.customer_id,
            "line_items": [li.to_dict() for li in self.line_items],
            "payments": [p.to_dict() for p in self.payments],
            "is_aggregated": self.is_aggregated,
        })
        return base


@dataclass(frozen=True)
class ReturnEvent(BaseEvent):
    """A return transaction event."""

    return_id: str
    store_id: str
    register_id: str
    employee_id: str
    line_items: tuple[LineItem, ...]
    return_reason_code: str
    price_determination: str  # "original", "current", "override"
    customer_id: str | None = None
    original_transaction_id: str | None = None  # None if reference_policy != ALWAYS

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.RETURN)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "return_id": self.return_id,
            "store_id": self.store_id,
            "register_id": self.register_id,
            "employee_id": self.employee_id,
            "customer_id": self.customer_id,
            "original_transaction_id": self.original_transaction_id,
            "line_items": [li.to_dict() for li in self.line_items],
            "return_reason_code": self.return_reason_code,
            "price_determination": self.price_determination,
        })
        return base


@dataclass(frozen=True)
class VoidEvent(BaseEvent):
    """A void/cancellation event."""

    void_id: str
    original_event_id: str
    original_event_type: EventType
    void_reason: str
    authorized_by: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.VOID)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "void_id": self.void_id,
            "original_event_id": self.original_event_id,
            "original_event_type": self.original_event_type.value,
            "void_reason": self.void_reason,
            "authorized_by": self.authorized_by,
        })
        return base


@dataclass(frozen=True)
class CorrectionEvent(BaseEvent):
    """A correction to a prior event."""

    correction_id: str
    original_event_id: str
    field_corrections: tuple[tuple[str, Any], ...]  # (field_name, new_value) pairs
    correction_reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.CORRECTION)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "correction_id": self.correction_id,
            "original_event_id": self.original_event_id,
            "field_corrections": {k: v for k, v in self.field_corrections},
            "correction_reason": self.correction_reason,
        })
        return base


@dataclass(frozen=True)
class InventoryAdjustmentEvent(BaseEvent):
    """A transactional inventory change."""

    adjustment_id: str
    store_id: str
    sku: str
    quantity_change: int
    reason_code: str
    reference_event_id: str | None = None  # Links to sale/return if applicable

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.INVENTORY_ADJUSTMENT)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "adjustment_id": self.adjustment_id,
            "store_id": self.store_id,
            "sku": self.sku,
            "quantity_change": self.quantity_change,
            "reason_code": self.reason_code,
            "reference_event_id": self.reference_event_id,
        })
        return base


@dataclass(frozen=True)
class InventorySnapshotEvent(BaseEvent):
    """A periodic inventory snapshot."""

    snapshot_id: str
    store_id: str
    sku: str
    quantity_on_hand: int
    snapshot_type: str  # "daily", "weekly", etc.

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.INVENTORY_SNAPSHOT)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "snapshot_id": self.snapshot_id,
            "store_id": self.store_id,
            "sku": self.sku,
            "quantity_on_hand": self.quantity_on_hand,
            "snapshot_type": self.snapshot_type,
        })
        return base


@dataclass(frozen=True)
class ProductChangeEvent(BaseEvent):
    """A product hierarchy or attribute change."""

    change_id: str
    sku: str
    change_type: str  # "hierarchy", "price", "status"
    old_value: str | None
    new_value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.PRODUCT_CHANGE)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "change_id": self.change_id,
            "sku": self.sku,
            "change_type": self.change_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
        })
        return base


@dataclass(frozen=True)
class StoreChangeEvent(BaseEvent):
    """A store lifecycle change."""

    change_id: str
    store_id: str
    change_type: str  # "open", "close", "merge"
    related_store_id: str | None = None  # For merges

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.STORE_CHANGE)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = super().to_dict()
        base.update({
            "change_id": self.change_id,
            "store_id": self.store_id,
            "change_type": self.change_type,
            "related_store_id": self.related_store_id,
        })
        return base


@dataclass
class EventLog:
    """Container for a sequence of events."""

    shop_config_seed: int
    events: list[BaseEvent] = field(default_factory=list)

    def to_json_lines(self) -> str:
        """Serialize to JSON Lines format."""
        import json

        lines = []
        for event in self.events:
            lines.append(json.dumps(event.to_dict()))
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "shop_config_seed": self.shop_config_seed,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }
