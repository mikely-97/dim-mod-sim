"""Enumeration types for shop configuration options."""

from enum import Enum


class TransactionGrain(str, Enum):
    """The level of detail at which transactions are recorded."""

    RECEIPT_LEVEL = "receipt_level"
    LINE_ITEM_LEVEL = "line_item_level"
    MIXED = "mixed"


class TimestampBusinessDateRelation(str, Enum):
    """Whether transaction timestamp and business date are the same or different."""

    SAME = "same"
    DIFFERENT = "different"


class ProductHierarchyChangeFrequency(str, Enum):
    """How often product hierarchy changes occur."""

    NONE = "none"
    OCCASIONAL = "occasional"
    FREQUENT = "frequent"


class CustomerIdReliability(str, Enum):
    """How reliable the customer ID is across transactions."""

    RELIABLE = "reliable"
    UNRELIABLE = "unreliable"
    ABSENT = "absent"


class PromotionsPerLineItem(str, Enum):
    """Whether line items can have one or many promotions."""

    ONE = "one"
    MANY = "many"


class ReturnsReferencePolicy(str, Enum):
    """Whether returns reference the original sale."""

    ALWAYS = "always"
    SOMETIMES = "sometimes"
    NEVER = "never"


class ReturnsPricingPolicy(str, Enum):
    """How return prices are determined."""

    ORIGINAL_PRICE = "original_price"
    CURRENT_PRICE = "current_price"
    ARBITRARY_OVERRIDE = "arbitrary_override"


class InventoryType(str, Enum):
    """How inventory is tracked."""

    TRANSACTIONAL = "transactional"
    PERIODIC_SNAPSHOT = "periodic_snapshot"
    BOTH = "both"


class Difficulty(str, Enum):
    """Difficulty level for shop generation."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADVERSARIAL = "adversarial"
